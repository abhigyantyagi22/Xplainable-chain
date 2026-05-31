"""
Etherscan / Polygonscan API client.

Provides real account and contract enrichment data to replace the hardcoded
feature estimates that were in feature_engineering.py:
  - sender_tx_count  : real confirmed outgoing tx count (eth_getTransactionCount)
  - contract_age     : days since contract deployment (from creation block timestamp)
  - median_gas_price : current network median gas price in Gwei (gas oracle)

All public methods return None on any failure so callers can fall back to
their existing estimates without crashing.

Phase 3 (Step 9): now uses the shared CacheService (Redis + in-memory fallback)
instead of a private dict, so cached values survive across requests and are
shared with other services that need the same data.
"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# Etherscan V2 unified endpoint — all networks use the same URL with chainid param
# Migration guide: https://docs.etherscan.io/v2-migration
_V2_URL = "https://api.etherscan.io/v2/api"

_CHAIN_IDS: Dict[str, int] = {
    "ethereum":     1,
    "polygon":      137,
    "polygon-amoy": 80002,
}

# Kept for backward compat with _base_url() calls
_EXPLORER_URLS: Dict[str, str] = {
    "ethereum":     _V2_URL,
    "polygon":      _V2_URL,
    "polygon-amoy": _V2_URL,
}

_GAS_TTL  = 300    # gas prices change fast — 5 min TTL
_DATA_TTL = 3600   # contract / account data — 1 hour TTL


class EtherscanService:
    """
    Async Etherscan/Polygonscan client.

    Pass a CacheService instance to share cached results across all requests
    (recommended).  Without one, each lookup hits the Etherscan API directly.
    """

    def __init__(
        self,
        api_key: str = "",
        polygon_api_key: str = "",
        cache=None,              # Optional[CacheService] — avoids circular import
    ):
        self._keys: Dict[str, str] = {
            "ethereum":     api_key,
            "polygon":      polygon_api_key or api_key,
            "polygon-amoy": polygon_api_key or api_key,
        }
        self._cache = cache  # CacheService instance (may be None)

        if not api_key:
            logger.warning(
                "EtherscanService: no API key — enrichment features will use fallback estimates"
            )

    # ── cache helpers (async, delegated to CacheService) ─────────────────────

    async def _cache_get(self, key: str) -> Optional[Any]:
        if self._cache is None:
            return None
        return await self._cache.get_json(key)

    async def _cache_set(self, key: str, value: Any, ttl: int = _DATA_TTL) -> None:
        if self._cache is not None:
            await self._cache.set_json(key, value, ttl=ttl)

    def _api_key(self, network: str) -> str:
        return self._keys.get(network, self._keys["ethereum"])

    def _base_url(self, network: str) -> str:
        return _V2_URL  # V2 uses a single unified endpoint for all networks

    def _chain_params(self, network: str) -> Dict[str, int]:
        """Return chainid param required by Etherscan V2."""
        return {"chainid": _CHAIN_IDS.get(network, 1)}

    # ── public methods ────────────────────────────────────────────────────────

    async def get_account_tx_count(
        self, address: str, network: str = "ethereum"
    ) -> Optional[int]:
        """
        Total confirmed outgoing transactions ever sent by this address.

        Uses eth_getTransactionCount at 'latest' which equals the account
        nonce — the exact number of confirmed outgoing transactions.
        This is the production-correct value for the 'sender_tx_count' feature.
        """
        if not self._api_key(network):
            return None

        key = f"txcount:{network}:{address.lower()}"
        cached = await self._cache_get(key)
        if cached is not None:
            return int(cached)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(self._base_url(network), params={
                    "module":  "proxy", **self._chain_params(network),
                    "action":  "eth_getTransactionCount",
                    "address": address,
                    "tag":     "latest",
                    "apikey":  self._api_key(network),
                })
            result = r.json().get("result", "")
            if result and result.startswith("0x"):
                count = int(result, 16)
                await self._cache_set(key, count, ttl=_DATA_TTL)
                logger.info(f"Etherscan: {address[:10]}… has {count} outgoing txs")
                return count
        except Exception as e:
            logger.warning(f"Etherscan tx_count failed ({address[:10]}…): {e}")

        return None

    async def get_contract_age_days(
        self, address: str, network: str = "ethereum"
    ) -> Optional[float]:
        """
        Age of a smart contract in days, measured from its creation block.

        Returns None when:
          - address is an EOA (has no creation record)
          - the API call fails or the key is missing
        Callers should treat None as 'unknown' and use a fallback estimate.
        """
        if not address or address == "0x" + "0" * 40:
            return None
        if not self._api_key(network):
            return None

        key = f"contract_age:{network}:{address.lower()}"
        cached = await self._cache_get(key)
        if cached is not None:
            return float(cached) if cached != "null" else None

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r1 = await client.get(self._base_url(network), params={
                    "module":            "contract",
                    "action":            "getcontractcreationinfo",
                    "contractaddresses": address,
                    "apikey":            self._api_key(network),
                    **self._chain_params(network),
                })
            data = r1.json()

            if data.get("status") != "1" or not data.get("result"):
                await self._cache_set(key, None, ttl=_DATA_TTL)
                return None

            creation_tx_hash = data["result"][0].get("txHash")
            if not creation_tx_hash:
                return None

            async with httpx.AsyncClient(timeout=8.0) as client:
                r2 = await client.get(self._base_url(network), params={
                    "module":  "proxy", **self._chain_params(network),
                    "action":  "eth_getTransactionByHash",
                    "txhash":  creation_tx_hash,
                    "apikey":  self._api_key(network),
                })
            tx = r2.json().get("result") or {}
            block_hex = tx.get("blockNumber")
            if not block_hex:
                return None

            async with httpx.AsyncClient(timeout=8.0) as client:
                r3 = await client.get(self._base_url(network), params={
                    "module":  "proxy", **self._chain_params(network),
                    "action":  "eth_getBlockByNumber",
                    "tag":     block_hex,
                    "boolean": "false",
                    "apikey":  self._api_key(network),
                })
            block = r3.json().get("result") or {}
            ts_hex = block.get("timestamp")
            if not ts_hex:
                return None

            import time
            creation_ts = int(ts_hex, 16)
            age_days = round(max(0.0, (time.time() - creation_ts) / 86400), 1)
            await self._cache_set(key, age_days, ttl=_DATA_TTL)
            logger.info(f"Etherscan: contract {address[:10]}… is {age_days} days old")
            return age_days

        except Exception as e:
            logger.warning(f"Etherscan contract_age failed ({address[:10]}…): {e}")

        return None

    async def get_network_gas_median(
        self, network: str = "ethereum"
    ) -> Optional[float]:
        """
        Current standard / median gas price in Gwei from Etherscan's gas oracle.

        Gas oracle is only available on Ethereum mainnet and Polygon mainnet.
        For testnets or unsupported networks, returns None.
        Uses a short 5-minute cache since gas prices change frequently.
        """
        if not self._api_key(network):
            return None
        if network not in ("ethereum", "polygon"):
            return None

        key = f"gas_median:{network}"
        cached = await self._cache_get(key)
        if cached is not None:
            return float(cached)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(self._base_url(network), params={
                    "module": "gastracker",
                    "action": "gasoracle",
                    "apikey": self._api_key(network),
                    **self._chain_params(network),
                })
            data = r.json()
            if data.get("status") == "1" and data.get("result"):
                median = float(data["result"]["ProposeGasPrice"])
                await self._cache_set(key, median, ttl=_GAS_TTL)
                logger.info(f"Etherscan gas oracle ({network}): {median} Gwei median")
                return median
        except Exception as e:
            logger.warning(f"Etherscan gas oracle failed ({network}): {e}")

        return None

    async def get_account_age_days(
        self, address: str, network: str = "ethereum"
    ) -> Optional[float]:
        """
        Days since the address's first recorded on-chain transaction.

        Works for both EOAs and contracts (unlike get_contract_age_days which
        only works for verified contracts with a creation record).
        """
        if not address or address == "0x" + "0" * 40:
            return None
        if not self._api_key(network):
            return None

        key = f"account_age:{network}:{address.lower()}"
        cached = await self._cache_get(key)
        if cached is not None:
            return float(cached)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(self._base_url(network), params={
                    "module":  "account",
                    "action":  "txlist",
                    "address": address,
                    "sort":    "asc",
                    "offset":  1,
                    "page":    1,
                    "apikey":  self._api_key(network),
                    **self._chain_params(network),
                })
            data = r.json()
            txs = data.get("result", [])
            if isinstance(txs, list) and txs:
                import time as _time
                first_ts = int(txs[0].get("timeStamp", _time.time()))
                age_days = round(max(0.0, (_time.time() - first_ts) / 86_400), 1)
                await self._cache_set(key, age_days, ttl=_DATA_TTL)
                logger.info(f"Etherscan: {address[:10]}… account age = {age_days:.1f} days")
                return age_days
        except Exception as e:
            logger.warning(f"Etherscan account_age_days failed ({address[:10]}…): {e}")

        return None
