"""
Async cache service — Redis with in-memory fallback.

Used for:
  • Full transaction analysis results  (TTL: ANALYSIS_CACHE_TTL, default 5 min)
  • Etherscan contract / account data  (TTL: 1 hour)
  • Network gas price median           (TTL: 5 minutes)

If Redis is unreachable or the redis package is not installed, every operation
falls back silently to an in-memory dict.  The app is fully functional either
way; Redis just adds cross-process persistence and avoids cache loss on restart.

Redis setup:
  pip install redis        (sync + async client, no extra package needed)
  Set REDIS_URL=redis://localhost:6379 in .env
  Docker Compose already includes a Redis service.
"""

import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CacheService:
    """
    Async key-value cache backed by Redis with transparent in-memory fallback.

    All values are stored as strings (JSON-serialised when needed).
    """

    def __init__(self, redis_url: str = ""):
        self._redis = None
        self._memory: Dict[str, Tuple[str, float]] = {}  # key → (value, expiry_ts)
        self._redis_available = False

        if redis_url:
            try:
                import redis.asyncio as aioredis  # type: ignore
                self._redis = aioredis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                self._redis_available = True
                logger.info(f"CacheService: Redis configured at {redis_url}")
            except ImportError:
                logger.warning(
                    "CacheService: 'redis' package not installed. "
                    "Install with: pip install redis  — falling back to in-memory cache"
                )
            except Exception as e:
                logger.warning(f"CacheService: Redis init failed ({e}) — using in-memory cache")

        if not self._redis_available:
            logger.info("CacheService: using in-memory fallback (single-process only)")

    # ── private helpers ───────────────────────────────────────────────────────

    async def _redis_get(self, key: str) -> Optional[str]:
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.debug(f"Redis GET failed ({e}) — falling back to memory")
            self._redis_available = False
            return None

    async def _redis_set(self, key: str, value: str, ttl: int) -> bool:
        try:
            await self._redis.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.debug(f"Redis SET failed ({e}) — falling back to memory")
            self._redis_available = False
            return False

    async def _redis_delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.debug(f"Redis DEL failed ({e})")

    def _mem_get(self, key: str) -> Optional[str]:
        entry = self._memory.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.monotonic() > expiry:
            del self._memory[key]
            return None
        return value

    def _mem_set(self, key: str, value: str, ttl: int) -> None:
        self._memory[key] = (value, time.monotonic() + ttl)

    def _mem_delete(self, key: str) -> None:
        self._memory.pop(key, None)

    # ── public API ────────────────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[str]:
        """Return the cached string for *key*, or None if missing / expired."""
        if self._redis_available:
            result = await self._redis_get(key)
            if result is not None:
                return result
        return self._mem_get(key)

    async def set(self, key: str, value: str, ttl: int = 300) -> None:
        """Cache *value* under *key* for *ttl* seconds."""
        if self._redis_available:
            stored = await self._redis_set(key, value, ttl)
            if stored:
                return
        self._mem_set(key, value, ttl)

    async def delete(self, key: str) -> None:
        """Remove *key* from both caches."""
        if self._redis_available:
            await self._redis_delete(key)
        self._mem_delete(key)

    async def get_json(self, key: str) -> Optional[Any]:
        """Retrieve and JSON-deserialise a cached value."""
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    async def set_json(self, key: str, value: Any, ttl: int = 300) -> None:
        """JSON-serialise *value* and cache it."""
        await self.set(key, json.dumps(value), ttl)

    async def healthcheck(self) -> dict:
        """Return cache backend status — used by /health endpoint."""
        if self._redis_available:
            try:
                await self._redis.ping()
                return {"backend": "redis", "status": "connected"}
            except Exception:
                pass
        mem_keys = len(self._memory)
        return {"backend": "memory", "status": "ok", "keys": mem_keys}
