"""
Address enrichment and threat-intelligence screening.

Screens Ethereum addresses against three sources before ML inference runs:

  1. OFAC SDN list  — US Treasury sanctions (Tornado Cash, Blender.io, etc.)
                      Hardcoded critical set + optional full-list download.
                      No API key required.

  2. Chainabuse     — Community-reported fraud addresses.
                      Optional: set CHAINABUSE_API_KEY in .env.
                      Results cached 24 hours.

  3. Internal MongoDB history — Addresses we have previously flagged
                      (risk_score >= HIGH_RISK_THRESHOLD in analysis_history).
                      Zero extra cost — reuses existing data.

Short-circuit rule
──────────────────
If any source flags an address, the caller should skip ML inference entirely
and return risk_score=100 immediately.  This saves compute and ensures
regulated entities (OFAC) are always blocked.

Usage
─────
    svc = EnrichmentService(chainabuse_api_key="...", cache=cache_svc, db=mongo_db)
    result = await svc.screen_address("0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b")
    if result.flagged:
        # short-circuit: return max risk without running the model
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

import httpx

from app.utils.fraud_addresses import OFAC_ADDRESSES, ALL_FRAUD_ADDRESSES

logger = logging.getLogger(__name__)

# Alias kept for internal use — the canonical set lives in fraud_addresses.py
_OFAC_SANCTIONED: frozenset = OFAC_ADDRESSES



@dataclass
class ScreeningResult:
    flagged: bool = False
    source: str = ""          # "ofac" | "chainabuse" | "internal" | ""
    detail: str = ""          # human-readable reason
    risk_override: int = 0    # 100 for OFAC, 85 for Chainabuse, 0 otherwise


class EnrichmentService:
    """
    Screens Ethereum addresses before ML inference.

    Pass a CacheService (cache=) and a MongoDB database (db=) to enable
    Chainabuse caching and internal-history lookup respectively.
    Both are optional — the service degrades gracefully without them.
    """

    _CHAINABUSE_BASE = "https://api.chainabuse.com/v0"
    _CHAINABUSE_CACHE_TTL = 86_400   # 24 hours

    def __init__(
        self,
        chainabuse_api_key: str = "",
        cache=None,     # Optional[CacheService]
        db=None,        # Optional[pymongo.Database]
        high_risk_threshold: int = 80,
    ):
        self._cb_key   = chainabuse_api_key or os.getenv("CHAINABUSE_API_KEY", "")
        self._cache    = cache
        self._db       = db
        self._hr_thresh = high_risk_threshold

        sources = ["OFAC (hardcoded)"]
        if self._cb_key:
            sources.append("Chainabuse")
        if self._db is not None:
            sources.append("internal MongoDB history")
        logger.info(f"EnrichmentService active sources: {', '.join(sources)}")

    # ── public API ─────────────────────────────────────────────────────────────

    async def screen_address(self, address: str) -> ScreeningResult:
        """
        Screen a single Ethereum address against all configured sources.

        Returns on first match (OFAC → Chainabuse → internal).
        Always returns a ScreeningResult; never raises.
        """
        if not address or len(address) < 10:
            return ScreeningResult()

        addr = address.lower()

        # 1. OFAC — instant, no I/O
        ofac = self._check_ofac(addr)
        if ofac:
            return ofac

        # 2. Chainabuse — async HTTP, cached
        cb = await self._check_chainabuse(addr)
        if cb:
            return cb

        # 3. Internal MongoDB history — sync query on cached connection
        internal = self._check_internal(addr)
        if internal:
            return internal

        return ScreeningResult()

    async def screen_transaction(
        self, sender: str, recipient: str
    ) -> ScreeningResult:
        """
        Screen both parties of a transaction.
        Returns the first flagged result, or a clean result.
        """
        for addr in (sender, recipient):
            if addr:
                result = await self.screen_address(addr)
                if result.flagged:
                    return result
        return ScreeningResult()

    # ── OFAC ───────────────────────────────────────────────────────────────────

    def _check_ofac(self, address: str) -> Optional[ScreeningResult]:
        if address in _OFAC_SANCTIONED:
            logger.warning(f"OFAC sanctioned address detected: {address[:12]}…")
            return ScreeningResult(
                flagged=True,
                source="ofac",
                detail="Address is on the OFAC SDN sanctions list.",
                risk_override=100,
            )
        return None

    # ── Chainabuse ─────────────────────────────────────────────────────────────

    async def _check_chainabuse(self, address: str) -> Optional[ScreeningResult]:
        if not self._cb_key:
            return None

        cache_key = f"chainabuse:{address}"

        # Check cache first
        if self._cache:
            try:
                cached = await self._cache.get_json(cache_key)
                if cached is not None:
                    return ScreeningResult(**cached) if cached.get("flagged") else None
            except Exception:
                pass

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self._chainabuse_base}/reports",
                    params={"address": address},
                    headers={"x-api-key": self._cb_key},
                )

            if r.status_code == 200:
                data   = r.json()
                total  = data.get("total", 0)
                reports = data.get("reports", [])

                if total > 0:
                    # Summarise abuse categories
                    categories = list({r.get("category", "unknown") for r in reports[:5]})
                    detail = (
                        f"Chainabuse: {total} fraud report(s). "
                        f"Categories: {', '.join(categories)}"
                    )
                    result = ScreeningResult(
                        flagged=True,
                        source="chainabuse",
                        detail=detail,
                        risk_override=85,
                    )
                    # Cache positive result for 24 hours
                    if self._cache:
                        try:
                            await self._cache.set_json(
                                cache_key,
                                {"flagged": True, "source": "chainabuse",
                                 "detail": detail, "risk_override": 85},
                                ttl=self._CHAINABUSE_CACHE_TTL,
                            )
                        except Exception:
                            pass
                    logger.warning(f"Chainabuse flagged {address[:12]}…: {detail}")
                    return result

                # Clean — cache negative for 1 hour (shorter, list updates regularly)
                if self._cache:
                    try:
                        await self._cache.set_json(
                            cache_key, {"flagged": False}, ttl=3600
                        )
                    except Exception:
                        pass

            elif r.status_code == 429:
                logger.warning("Chainabuse rate limit hit — skipping check")
            else:
                logger.debug(f"Chainabuse returned {r.status_code} for {address[:12]}…")

        except Exception as e:
            logger.debug(f"Chainabuse check failed ({address[:12]}…): {e}")

        return None

    # ── Internal MongoDB history ───────────────────────────────────────────────

    def _check_internal(self, address: str) -> Optional[ScreeningResult]:
        if self._db is None:
            return None
        try:
            col = self._db["analysis_history"]
            doc = col.find_one(
                {
                    "$or": [
                        {"features.sender_address": address},
                        {"tx_data.from": address},
                        {"tx_data.to": address},
                    ],
                    "risk_score": {"$gte": self._hr_thresh},
                },
                sort=[("analyzed_at", -1)],
            )
            if doc:
                score = doc.get("risk_score", 0)
                tx    = doc.get("tx_hash", "unknown")
                detail = (
                    f"Previously flagged with risk_score={score} "
                    f"(tx: {tx[:14]}…)"
                )
                logger.info(f"Internal history flagged {address[:12]}…: {detail}")
                return ScreeningResult(
                    flagged=True,
                    source="internal",
                    detail=detail,
                    risk_override=min(100, score + 10),  # slight uplift for repeat offender
                )
        except Exception as e:
            logger.debug(f"Internal history check failed ({address[:12]}…): {e}")
        return None

    @property
    def _chainabuse_base(self):
        return self._CHAINABUSE_BASE
