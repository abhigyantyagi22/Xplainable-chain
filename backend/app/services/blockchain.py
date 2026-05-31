from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    # For older web3.py versions
    from web3.middleware import geth_poa_middleware
from eth_account import Account
import json
import os
from typing import Optional, Dict
import logging
from pathlib import Path
from fastapi import HTTPException
from dotenv import load_dotenv

from app.services.etherscan import EtherscanService
from app.services.cache import CacheService
from app.utils.graph_features import compute_graph_features

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class BlockchainService:
    """Web3 service for blockchain interactions"""
    
    def __init__(self):
        """Initialize Web3 connection"""
        # Shared cache (Redis → in-memory fallback) used by EtherscanService and graph features
        self._cache = CacheService(redis_url=os.getenv("REDIS_URL", ""))

        # Etherscan enrichment service (provides real contract age, gas median, tx count)
        self.etherscan = EtherscanService(
            api_key=os.getenv("ETHERSCAN_API_KEY", ""),
            polygon_api_key=os.getenv("POLYGONSCAN_API_KEY", ""),
            cache=self._cache,
        )

        # Get Infura API key
        infura_key = os.getenv("INFURA_API_KEY", "")
        
        # Setup network RPCs
        self.network_rpcs = {
            "ethereum": os.getenv("ETHEREUM_MAINNET_RPC", f"https://mainnet.infura.io/v3/{infura_key}"),
            "polygon": os.getenv("POLYGON_MAINNET_RPC", f"https://polygon-mainnet.infura.io/v3/{infura_key}"),
            "polygon-amoy": os.getenv("POLYGON_AMOY_RPC", f"https://polygon-amoy.infura.io/v3/{infura_key}"),
        }
        
        # Default Web3 connection (Polygon Amoy)
        default_rpc = os.getenv("INFURA_URL", self.network_rpcs["polygon-amoy"])
        self.w3 = Web3(Web3.HTTPProvider(default_rpc))
        # Inject PoA middleware for Polygon Amoy (default network)
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        logger.info(" Injected PoA middleware for default Web3 instance (Polygon Amoy)")
        
        # Web3 instances for different networks
        self.network_w3 = {}
        for network, rpc in self.network_rpcs.items():
            try:
                w3_instance = Web3(Web3.HTTPProvider(rpc))
                
                # Add PoA middleware for Polygon networks (Proof of Authority chains)
                if network.startswith('polygon'):
                    w3_instance.middleware_onion.inject(geth_poa_middleware, layer=0)
                    logger.info(f" Injected PoA middleware for {network}")
                
                self.network_w3[network] = w3_instance
                is_connected = w3_instance.is_connected()
                logger.info(f"Network '{network}' - RPC: {rpc} - Connected: {is_connected}")
            except Exception as e:
                logger.error(f"Failed to initialize Web3 for {network}: {e}")
        
        # Load contract
        contract_address = os.getenv("CONTRACT_ADDRESS")
        
        # Try to load contract ABI (check backend/abi first, then frontend/public/abi)
        abi_path = Path(__file__).parent.parent.parent / "abi" / "XAIChainVerifier.json"
        if not abi_path.exists():
            abi_path = Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "abi" / "XAIChainVerifier.json"
        
        try:
            if abi_path.exists():
                with open(abi_path, "r") as f:
                    contract_data = json.load(f)
                    contract_abi = contract_data.get('abi', [])
            else:
                logger.warning(f"Contract ABI not found at {abi_path}")
                contract_abi = self._get_mock_abi()
            
            if contract_address and contract_address != "":
                self.contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(contract_address),
                    abi=contract_abi
                )
            else:
                logger.warning("Contract address not set. Blockchain storage will be mocked.")
                self.contract = None
            
            # Load private key for transactions
            private_key = os.getenv("PRIVATE_KEY")
            if private_key and private_key != "":
                self.account = Account.from_key(private_key)
            else:
                logger.warning("Private key not set. Transactions will be mocked.")
                self.account = None
            
            logger.info(f"Blockchain service initialized. Connected: {self.w3.is_connected()}")
        except Exception as e:
            logger.error(f"Failed to initialize blockchain service: {e}")
            self.contract = None
            self.account = None
    
    def _get_mock_abi(self):
        """Return a mock ABI for testing"""
        return [
            {
                "inputs": [
                    {"internalType": "bytes32", "name": "_txHash", "type": "bytes32"},
                    {"internalType": "string", "name": "_ipfsHash", "type": "string"},
                    {"internalType": "uint8", "name": "_riskScore", "type": "uint8"}
                ],
                "name": "storeExplanation",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    async def get_transaction(self, tx_hash: str, network: str = "ethereum") -> Optional[Dict]:
        """
        Fetch REAL transaction data from blockchain
        
        Args:
            tx_hash: Transaction hash (with 0x prefix)
            network: Blockchain network (ethereum, polygon, polygon-amoy)
        
        Returns:
            Transaction data dictionary with extracted features
        """
        try:
            # Get Web3 instance for the specified network
            w3 = self.network_w3.get(network, self.w3)
            
            if not w3.is_connected():
                logger.error(f"Web3 not connected to {network}")
                raise HTTPException(status_code=503, detail=f"Cannot connect to {network} network")
            
            logger.info(f"Fetching transaction {tx_hash} from {network}")
            
            # Fetch transaction data
            tx = w3.eth.get_transaction(tx_hash)
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            
            # Current confirmed tx count for the sender (= current nonce)
            sender_tx_count = w3.eth.get_transaction_count(tx['from'])

            # Receiver tx count (if to address exists)
            receiver_tx_count = 0
            if tx['to']:
                receiver_tx_count = w3.eth.get_transaction_count(tx['to'])

            # Block data — gasUsed / gasLimit gives the real block utilisation ratio
            block = w3.eth.get_block(tx['blockNumber'])
            timestamp = block['timestamp']
            block_gas_limit = block.get('gasLimit', 30_000_000)
            block_gas_used  = block.get('gasUsed', 0)
            block_gas_used_ratio = float(block_gas_used) / float(block_gas_limit) if block_gas_limit else 0.5

            from datetime import datetime
            time_of_day = datetime.fromtimestamp(timestamp).hour

            contract_interaction = 1 if (tx['to'] and len(tx.get('input', '0x')) > 2) else 0
            unique_addresses = len(set([tx['from'], tx['to']]) - {None})
            num_transfers = len(receipt.get('logs', []))

            amount    = float(w3.from_wei(tx['value'], 'ether'))
            gas_price = float(w3.from_wei(tx['gasPrice'], 'gwei'))
            gas_used  = receipt['gasUsed']

            # ── Etherscan enrichment (all calls are best-effort; None = use fallback) ──
            to_address = tx['to'] if tx['to'] else ''

            # Real contract age — replaces the hardcoded 30-day estimate
            contract_age = await self.etherscan.get_contract_age_days(to_address, network)

            # Real network median gas price — replaces the hardcoded 50 Gwei constant
            median_gas = await self.etherscan.get_network_gas_median(network)

            # Real confirmed sender tx count — Etherscan value preferred over Web3 nonce
            # because Web3 nonce counts only outgoing txs; Etherscan total may include
            # internal txs on some networks. Falls back to the Web3 value if API fails.
            etherscan_tx_count = await self.etherscan.get_account_tx_count(tx['from'], network)
            if etherscan_tx_count is not None:
                sender_tx_count = etherscan_tx_count

            # ── Graph features (new — require Etherscan history lookup) ─────────
            # sender_fraud_neighbor_ratio: indirect fraud exposure via recent counterparties
            # sender_account_age_days: freshly-created wallets are higher risk
            graph = await compute_graph_features(
                sender=tx['from'],
                network=network,
                api_key=os.getenv("ETHERSCAN_API_KEY", ""),
                cache=self._cache,
            )

            logger.info(
                f"Enrichment for {tx_hash[:12]}…: "
                f"contract_age={contract_age} days, "
                f"median_gas={median_gas} Gwei, "
                f"sender_tx_count={sender_tx_count}, "
                f"block_gas_ratio={block_gas_used_ratio:.3f}, "
                f"fraud_neighbor_ratio={graph['sender_fraud_neighbor_ratio']:.3f}, "
                f"account_age={graph['sender_account_age_days']:.1f} days"
            )

            return {
                'hash': tx_hash,
                'from': tx['from'],
                'to':   to_address,

                # Raw Web3 fields (consumed by extract_features)
                'value':       int(tx['value']),       # Wei
                'gasPrice':    int(tx['gasPrice']),    # Wei
                'gas':         int(tx.get('gas', gas_used)),
                'nonce':       int(tx['nonce']),
                'input':       tx.get('input', '0x'),
                'blockNumber': int(tx['blockNumber']),

                # Enriched fields — extract_features reads these first before
                # falling back to its own estimates
                'sender_tx_count':             sender_tx_count,
                'block_gas_used_ratio':        block_gas_used_ratio,
                'contract_age':                contract_age,   # None if EOA or API failed
                'median_gas':                  median_gas,     # None if API failed

                # Graph features (new — require Etherscan history lookup)
                'sender_fraud_neighbor_ratio': graph['sender_fraud_neighbor_ratio'],
                'sender_account_age_days':     graph['sender_account_age_days'],

                # Pre-processed fields kept for backward compatibility
                'amount':             amount,
                'gas_price':          gas_price,
                'gas_used':           gas_used,
                'num_transfers':      num_transfers,
                'unique_addresses':   unique_addresses,
                'time_of_day':        time_of_day,
                'contract_interaction': contract_interaction,
                'receiver_tx_count':  receiver_tx_count,
                'block_number':       tx['blockNumber'],
                'timestamp':          timestamp,
                'network':            network,
            }
        except Exception as e:
            logger.error(f"Error fetching transaction {tx_hash}: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            # Return None instead of mock data - let the caller handle the error
            raise HTTPException(
                status_code=404,
                detail=f"Transaction not found or error fetching from {network}: {str(e)}"
            )
    
    def _get_mock_transaction(self, tx_hash: str) -> Dict:
        """Return mock transaction data for testing"""
        import random
        return {
            'hash': tx_hash,
            'from': '0x' + '1' * 40,
            'to': '0x' + '2' * 40,
            'value': random.uniform(0.1, 10.0),
            'gas': random.randint(21000, 100000),
            'gas_price': random.uniform(20, 100),
            'gas_used': random.randint(21000, 90000),
            'block_number': random.randint(1000000, 2000000),
            'timestamp': 1609459200,
            'input': '0x'
        }
    
    async def store_explanation(
        self,
        tx_hash: str,
        ipfs_hash: str,
        risk_score: int
    ) -> str:
        """
        Store explanation on blockchain
        
        Args:
            tx_hash: Transaction hash being analyzed
            ipfs_hash: IPFS CID of explanation
            risk_score: Risk score 0-100
        
        Returns:
            Transaction hash of storage transaction
            
        Raises:
            HTTPException: If blockchain storage fails
        """
        try:
            if not self.contract or not self.account:
                logger.error("Blockchain storage FAILED: Contract or account not configured")
                raise HTTPException(
                    status_code=503,
                    detail="Blockchain storage not configured. Please check CONTRACT_ADDRESS and PRIVATE_KEY in environment."
                )
            
            # Convert tx_hash to bytes32
            tx_hash_bytes = Web3.to_bytes(hexstr=tx_hash)
            
            logger.info(f"Storing explanation on blockchain for tx: {tx_hash}")
            logger.info(f"IPFS hash: {ipfs_hash}, Risk score: {risk_score}")
            
            # Build transaction
            txn = self.contract.functions.storeExplanation(
                tx_hash_bytes,
                ipfs_hash,
                risk_score
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send
            signed_txn = self.account.sign_transaction(txn)
            tx_hash_result = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"Transaction sent, waiting for confirmation...")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_result)
            
            result_hash = receipt['transactionHash'].hex()
            logger.info(f" Stored on blockchain: {result_hash}")
            logger.info(f" Block number: {receipt['blockNumber']}, Gas used: {receipt['gasUsed']}")
            return result_hash
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Blockchain storage error: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to store on blockchain: {str(e)}"
            )

