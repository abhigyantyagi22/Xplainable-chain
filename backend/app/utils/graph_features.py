"""
Graph feature computation for real-time transaction analysis.

Computes two features that capture the network context of a transaction
— information that a single transaction's fields cannot provide:

  sender_fraud_neighbor_ratio
    Fraction of the sender's recent transaction counterparties that appear
    in the known fraud address registry (fraud_addresses.py).
    Range: 0.0 (never dealt with fraud wallets) – 1.0 (all recent partners are fraud).
    Signal: money mules and compromised accounts often show intermediate values (0.1–0.5)
            even before they're on the OFAC list.

  sender_account_age_days
    Days since the sender's first recorded on-chain transaction.
    Signal: freshly-created wallets (< 7 days) combined with large transfers
            is a strong fraud indicator.

Both features are fetched from Etherscan and cached via CacheService
(Redis → in-memory fallback) to avoid repeated API calls for the same address.

Fallback values when Etherscan is unavailable:
  sender_fraud_neighbor_ratio  → 0.0  (assume clean)
  sender_account_age_days      → 365.0  (assume established account)
"""

import logging
import time
from typing import Dict, Optional, Tuple

import httpx

from app.utils.fraud_addresses import ALL_FRAUD_ADDRESSES

logger = logging.getLogger(__name__)

# Etherscan V2 unified endpoint — all networks, add chainid param per request
_V2_URL = "https://api.etherscan.io/v2/api"

_CHAIN_IDS = {
    "ethereum":     1,
    "polygon":      137,
    "polygon-amoy": 80002,
}

_EXPLORER = {
    "ethereum":     _V2_URL,
    "polygon":      _V2_URL,
    "polygon-amoy": _V2_URL,
}

# How many recent counterparties to check for fraud exposure
_NEIGHBOR_SAMPLE_SIZE = 20


async def compute_graph_features(
    sender: str,
    network: str = "ethereum",
    api_key: str = "",
    cache=None,          # Optional[CacheService]
) -> Dict[str, float]:
    """
    Compute graph features for a given sender address.

    Args:
        sender:   Sender Ethereum address (lowercase)
        network:  Blockchain network
        api_key:  Etherscan / Polygonscan API key
        cache:    CacheService instance for result caching

    Returns:
        Dict with sender_fraud_neighbor_ratio and sender_account_age_days.
        Falls back to safe defaults on any error.
    """
    defaults = {
        "sender_fraud_neighbor_ratio": 0.0,
        "sender_account_age_days":     365.0,
    }

    if not sender or not api_key:
        return defaults

    sender = sender.lower()
    cache_key = f"graph:{network}:{sender}"

    # Check cache first
    if cache is not None:
        try:
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
        except Exception:
            pass

    base = _EXPLORER.get(network, _V2_URL)

    fraud_ratio = await _compute_fraud_neighbor_ratio(sender, base, api_key, network)
    account_age = await _compute_account_age_days(sender, base, api_key, network)

    result = {
        "sender_fraud_neighbor_ratio": fraud_ratio,
        "sender_account_age_days":     account_age,
    }

    # Cache for 1 hour — address history is stable over short periods
    if cache is not None:
        try:
            await cache.set_json(cache_key, result, ttl=3600)
        except Exception:
            pass

    logger.debug(
        f"Graph features for {sender[:10]}…: "
        f"fraud_neighbor_ratio={fraud_ratio:.3f}, "
        f"account_age={account_age:.1f} days"
    )
    return result


async def _compute_fraud_neighbor_ratio(
    address: str,
    base_url: str,
    api_key: str,
    network: str = "ethereum",
) -> float:
    """Fraction of recent counterparties in the known fraud set."""
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(base_url, params={
                "module":  "account",
                "action":  "txlist",
                "address": address,
                "sort":    "desc",
                "offset":  _NEIGHBOR_SAMPLE_SIZE,
                "page":    1,
                "apikey":  api_key,
                "chainid": _CHAIN_IDS.get(network, 1),
            })
        data = r.json()
        txs = data.get("result", [])
        if not isinstance(txs, list) or not txs:
            return 0.0

        counterparties = set()
        for tx in txs:
            for field in ("from", "to"):
                addr = tx.get(field, "").lower()
                if addr and addr != address:
                    counterparties.add(addr)

        if not counterparties:
            return 0.0

        fraud_count = sum(1 for a in counterparties if a in ALL_FRAUD_ADDRESSES)
        return round(fraud_count / len(counterparties), 4)

    except Exception as e:
        logger.debug(f"fraud_neighbor_ratio failed for {address[:10]}…: {e}")
        return 0.0


async def _compute_account_age_days(
    address: str,
    base_url: str,
    api_key: str,
    network: str = "ethereum",
) -> float:
    """Days since the address's first recorded transaction."""
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(base_url, params={
                "module":  "account",
                "action":  "txlist",
                "address": address,
                "sort":    "asc",
                "offset":  1,
                "page":    1,
                "apikey":  api_key,
                "chainid": _CHAIN_IDS.get(network, 1),
            })
        data = r.json()
        txs = data.get("result", [])
        if not isinstance(txs, list) or not txs:
            return 365.0  # unknown → assume established

        first_ts = int(txs[0].get("timeStamp", time.time()))
        age = max(0.0, (time.time() - first_ts) / 86_400)
        return round(age, 1)

    except Exception as e:
        logger.debug(f"account_age_days failed for {address[:10]}…: {e}")
        return 365.0
