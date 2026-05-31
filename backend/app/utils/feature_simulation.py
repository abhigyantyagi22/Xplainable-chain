"""
Feature Simulation for Pre-Transaction Analysis
Simulates transaction features WITHOUT requiring a real transaction.
This enables prevention instead of just post-transaction analysis.
"""

from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    # For older web3.py versions
    try:
        from web3.middleware import geth_poa_middleware
    except ImportError:
        geth_poa_middleware = None
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureSimulator:
    """Simulates transaction features for pre-transaction risk assessment"""
    
    def __init__(self, w3: Web3):
        self.w3 = w3
    
    def simulate_transaction_features(
        self,
        to_address: str,
        amount: float = 0,
        gas_price: Optional[int] = None,
        from_address: Optional[str] = None,
        gas_limit: Optional[int] = None
    ) -> Dict:
        """
        Simulate features for a transaction BEFORE it's sent.
        This is the key fix - we create features WITHOUT a real transaction.
        
        Args:
            to_address: Recipient address
            amount: Amount in ETH
            gas_price: Gas price in Gwei (optional, uses network average if None)
            from_address: Sender address (optional, for history)
            gas_limit: Gas limit (optional, estimated if None)
            
        Returns:
            Dictionary of simulated features matching model training format
        """
        try:
            # Validate and checksum the address
            try:
                to_address = self.w3.to_checksum_address(to_address)
            except Exception as e:
                logger.error(f"Invalid address format: {e}")
                raise ValueError(f"Invalid Ethereum address: {to_address}")
            
            # Get current network state
            current_block = self.w3.eth.get_block('latest')
            avg_gas_price = self.w3.eth.gas_price / 1e9  # Convert to Gwei
            
            # Use provided gas price or default to network average
            # Handle None, 0, or negative values
            if gas_price is None or gas_price <= 0:
                gas_price = max(int(avg_gas_price), 1)  # Ensure at least 1 Gwei
            
            
            # Convert amount to Wei
            amount_wei = int(amount * 1e18) if amount else 0
            
            # Check if recipient is a contract
            code = self.w3.eth.get_code(to_address)
            is_contract = len(code) > 2  # "0x" means no code
            
            # Estimate gas usage
            if gas_limit is None:
                if is_contract:
                    gas_used = 100000  # Typical contract interaction
                else:
                    gas_used = 21000  # Standard transfer
            else:
                gas_used = gas_limit
            
            # Calculate gas price deviation
            gas_price_deviation = (gas_price - avg_gas_price) / avg_gas_price if avg_gas_price > 0 else 0
            
            # Get sender transaction count (account age indicator)
            if from_address:
                try:
                    from_address_checksum = self.w3.to_checksum_address(from_address)
                    sender_tx_count = self.w3.eth.get_transaction_count(from_address_checksum)
                    logger.info(f"✅ Fetched real sender_tx_count: {sender_tx_count} for {from_address_checksum}")
                except Exception as e:
                    logger.warning(f"Could not fetch sender tx count: {e}")
                    # Use realistic variation for simulated accounts (not always 100)
                    import random
                    sender_tx_count = random.randint(50, 500)  # More realistic range for benign users
            else:
                # Use realistic variation for simulated accounts (not always 100)
                import random
                sender_tx_count = random.randint(50, 500)  # More realistic range for benign users
                logger.info(f"📊 Simulated sender_tx_count (no from_address): {sender_tx_count}")
            
            # Determine if this is contract creation
            is_contract_creation = 1 if (to_address == "0x0000000000000000000000000000000000000000") else 0
            
            # Estimate contract age (if sending to contract)
            contract_age = 0
            if is_contract and not is_contract_creation:
                # Use code size as heuristic for contract maturity
                # Add realistic variation instead of fixed values
                import random
                code_size = len(code)
                if code_size < 100:
                    contract_age = random.randint(1, 7)  # Very new or simple contract
                elif code_size < 1000:
                    contract_age = random.randint(7, 60)  # Recent contract
                else:
                    contract_age = random.randint(30, 365)  # Established contract
                logger.info(f"📊 Estimated contract_age: {contract_age} days (code_size: {code_size})")
            
            # Calculate block gas usage ratio
            block_gas_used_ratio = current_block.gasUsed / current_block.gasLimit if current_block.gasLimit > 0 else 0.5
            
            # Return features in the same format as training data
            features = {
                "amount": amount,
                "gas_price": gas_price,
                "gas_used": gas_used,
                "gas_price_deviation": gas_price_deviation,
                "value": amount,  # Same as amount for simple transfers
                "sender_tx_count": sender_tx_count,
                "is_contract_creation": is_contract_creation,
                "contract_age": contract_age,
                "block_gas_used_ratio": block_gas_used_ratio
            }
            
            logger.info(f"Simulated features for {to_address}: {features}")
            return features
            
        except Exception as e:
            logger.error(f"Error simulating features: {e}")
            raise
    
    def get_address_risk_indicators(self, address: str) -> Dict:
        """
        Quick risk indicators for an address (instant check).
        Used for ultra-fast pre-screening before full ML analysis.
        
        Returns:
            Dictionary with risk indicators
        """
        try:
            risk_indicators = {
                "is_contract": False,
                "transaction_count": 0,
                "code_size": 0,
                "estimated_age": "unknown"
            }
            
            # Check if it's a contract
            code = self.w3.eth.get_code(address)
            if len(code) > 2:
                risk_indicators["is_contract"] = True
                risk_indicators["code_size"] = len(code)
                
                # Estimate age based on code size (heuristic)
                if risk_indicators["code_size"] < 100:
                    risk_indicators["estimated_age"] = "very_new"
                elif risk_indicators["code_size"] < 1000:
                    risk_indicators["estimated_age"] = "recent"
                else:
                    risk_indicators["estimated_age"] = "established"
            
            # Get transaction count
            try:
                risk_indicators["transaction_count"] = self.w3.eth.get_transaction_count(address)
            except:
                pass
            
            return risk_indicators
            
        except Exception as e:
            logger.error(f"Error getting address indicators: {e}")
            return {
                "is_contract": False,
                "transaction_count": 0,
                "code_size": 0,
                "estimated_age": "unknown"
            }


def create_feature_simulator(rpc_url: str) -> FeatureSimulator:
    """Factory function to create a FeatureSimulator instance"""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Add POA middleware for Polygon and other POA chains
    if geth_poa_middleware:
        try:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            logger.info("✅ Injected PoA middleware for feature simulator")
        except Exception as e:
            logger.warning(f"Failed to inject PoA middleware: {e}")
    else:
        logger.warning("⚠️ PoA middleware not available - may fail on PoA chains")
    
    return FeatureSimulator(w3)
