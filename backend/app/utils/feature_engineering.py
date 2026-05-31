"""
Feature engineering for ML model inference.

extract_features() is called with the dict returned by BlockchainService.get_transaction().
That dict carries enriched fields populated by EtherscanService and graph_features.py.
Each feature reads the enriched value first and falls back to a safe estimate only
when Etherscan was unavailable (no API key, rate-limited, or network error).

Feature set (11 features)
──────────────────────────
  Original 9 transaction features:
    amount, gas_price, gas_used, gas_price_deviation, value,
    sender_tx_count, is_contract_creation, contract_age, block_gas_used_ratio

  Graph features (added for production — trained on real transaction-level data):
    sender_fraud_neighbor_ratio  → fraction of sender's recent counterparties
                                   in the known fraud address registry (0.0–1.0)
                                   Fallback: 0.0 (assume clean)
    sender_account_age_days      → days since sender's first on-chain tx
                                   Fallback: 365.0 (assume established account)

Fallback behaviour per feature
───────────────────────────────
  sender_tx_count              → nonce
  contract_age                 → 30 days for contracts, 0 for EOAs
  block_gas_used_ratio         → gas_used / 30 000 000
  gas_price_deviation          → deviation from 50 Gwei
  sender_fraud_neighbor_ratio  → 0.0
  sender_account_age_days      → 365.0
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Fallback constants used when Etherscan enrichment is unavailable
_FALLBACK_MEDIAN_GAS_GWEI = 50.0
_FALLBACK_CONTRACT_AGE_DAYS = 30.0
_STANDARD_BLOCK_GAS_LIMIT = 30_000_000


def extract_features(tx_data: Dict) -> Dict:
    """
    Build the 9-feature vector the XGBoost model expects.

    Feature order must match ai_detector.py and the trained model:
      amount, gas_price, gas_used, gas_price_deviation,
      value, sender_tx_count, is_contract_creation,
      contract_age, block_gas_used_ratio

    Args:
        tx_data: Dict returned by BlockchainService.get_transaction().
                 May contain enriched fields (contract_age, median_gas,
                 sender_tx_count, block_gas_used_ratio) set by EtherscanService.
                 All raw monetary values are in Wei.

    Returns:
        Dict with exactly the 9 model features.
    """
    features: Dict = {}

    # ── Features 1 & 5: amount / value ───────────────────────────────────────
    # RPC always returns Wei; divide by 1e18 unconditionally.
    value_wei = tx_data.get('value', 0)
    value_eth = float(value_wei) / 1e18 if value_wei else 0.0
    features['amount'] = value_eth
    features['value']  = value_eth

    # ── Feature 2: gas_price (Gwei) ───────────────────────────────────────────
    gas_price_wei = tx_data.get('gasPrice', tx_data.get('gas_price', 50_000_000_000))
    gas_price_gwei = float(gas_price_wei) / 1e9
    features['gas_price'] = gas_price_gwei

    # ── Feature 3: gas_used ───────────────────────────────────────────────────
    features['gas_used'] = int(tx_data.get('gas', tx_data.get('gas_used', 21_000)))

    # ── Feature 4: gas_price_deviation ───────────────────────────────────────
    # Use the real network median from Etherscan when available.
    median_gas: float = tx_data.get('median_gas') or _FALLBACK_MEDIAN_GAS_GWEI
    if median_gas <= 0:
        median_gas = _FALLBACK_MEDIAN_GAS_GWEI
    features['gas_price_deviation'] = abs(gas_price_gwei - median_gas) / median_gas
    if tx_data.get('median_gas') is None:
        logger.debug("gas_price_deviation: using fallback median of 50 Gwei")

    # ── Feature 6: sender_tx_count ────────────────────────────────────────────
    # Preference order:
    #   1. Etherscan confirmed count (set by blockchain.py after enrichment)
    #   2. Web3 get_transaction_count result (also in tx_data as 'sender_tx_count')
    #   3. nonce (count of outgoing txs at the time this tx was submitted)
    sender_tx_count = (
        tx_data.get('sender_tx_count')       # real count from Web3 / Etherscan
        or int(tx_data.get('nonce', 0))      # nonce fallback
    )
    features['sender_tx_count'] = int(sender_tx_count)

    # ── Feature 7: is_contract_creation ───────────────────────────────────────
    to_address = tx_data.get('to', '')
    is_null_address = (
        not to_address
        or to_address == '0x' + '0' * 40
    )
    features['is_contract_creation'] = 1 if is_null_address else 0

    # ── Feature 8: contract_age (days) ───────────────────────────────────────
    # Use the real age fetched by EtherscanService when available.
    # None means the address is an EOA or the API call failed.
    enriched_age: Optional[float] = tx_data.get('contract_age')

    if enriched_age is not None:
        features['contract_age'] = float(enriched_age)
    elif not is_null_address:
        # Recipient is an address (possibly a contract) but we couldn't get its age
        features['contract_age'] = _FALLBACK_CONTRACT_AGE_DAYS
        logger.debug("contract_age: Etherscan unavailable, using 30-day fallback")
    else:
        features['contract_age'] = 0.0

    # ── Feature 9: block_gas_used_ratio ──────────────────────────────────────
    # Use the real block utilisation computed from block.gasUsed / block.gasLimit
    # in blockchain.py. Falls back to gas_used / standard_limit estimate.
    enriched_ratio: Optional[float] = tx_data.get('block_gas_used_ratio')
    if enriched_ratio is not None:
        features['block_gas_used_ratio'] = float(enriched_ratio)
    else:
        features['block_gas_used_ratio'] = min(
            float(features['gas_used']) / _STANDARD_BLOCK_GAS_LIMIT, 1.0
        )
        logger.debug("block_gas_used_ratio: using gas_used / 30M estimate")

    # ── Feature 10: sender_fraud_neighbor_ratio ──────────────────────────────
    # Graph feature: fraction of sender's recent counterparties in fraud set.
    # Fallback: 0.0 (assume clean when Etherscan unavailable)
    features['sender_fraud_neighbor_ratio'] = float(
        tx_data.get('sender_fraud_neighbor_ratio', 0.0) or 0.0
    )

    # ── Feature 11: sender_account_age_days ──────────────────────────────────
    # Days since the sender's first on-chain transaction.
    # Fallback: 365.0 (assume established account — conservative, avoids false positives)
    features['sender_account_age_days'] = float(
        tx_data.get('sender_account_age_days', 365.0) or 365.0
    )

    logger.info(
        f"Extracted features — "
        f"amount={features['amount']:.4f} ETH, "
        f"gas_price={features['gas_price']:.1f} Gwei, "
        f"sender_tx_count={features['sender_tx_count']}, "
        f"contract_age={features['contract_age']} days, "
        f"block_gas_ratio={features['block_gas_used_ratio']:.3f}, "
        f"fraud_neighbor_ratio={features['sender_fraud_neighbor_ratio']:.3f}, "
        f"account_age={features['sender_account_age_days']:.1f} days"
    )

    return features
