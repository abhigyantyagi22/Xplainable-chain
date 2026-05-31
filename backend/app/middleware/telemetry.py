"""
Request telemetry middleware.

Records per-request observability data:
  - endpoint, method, HTTP status, latency_ms, client identity

Written to MongoDB `request_metrics` collection in a fire-and-forget
background thread — adds zero latency to the response path.

Also maintains in-memory counters so /api/metrics can respond instantly
even when MongoDB is unavailable.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Deque, Dict, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ── In-memory ring-buffer of recent requests ───────────────────────────────────
# Holds (timestamp, latency_ms, status_code, endpoint) tuples.
# Capped at 10 000 entries — old entries auto-evict.
_MAX_BUFFER = 10_000
_lock = threading.Lock()
_buffer: Deque[Tuple[float, float, int, str]] = deque(maxlen=_MAX_BUFFER)

# Cumulative counters (never reset — used for all-time totals)
_totals: Dict[str, int] = defaultdict(int)


def get_buffer_snapshot() -> list:
    """Return a copy of the in-memory buffer for metrics computation."""
    with _lock:
        return list(_buffer)


def get_totals() -> Dict[str, int]:
    with _lock:
        return dict(_totals)


# ── Middleware ─────────────────────────────────────────────────────────────────

class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    Measures wall-clock latency for every HTTP request and records it
    to an in-memory ring-buffer (always) and MongoDB (if available).
    """

    # Paths that generate a lot of noise but carry no signal
    _SKIP = {"/health", "/", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app, collection=None):
        """
        Args:
            collection: pymongo Collection for `request_metrics`.
                        If None, tries to pick it up from app.state.mongo_db on first request.
        """
        super().__init__(app)
        self._col = collection
        self._col_resolved = collection is not None

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self._SKIP:
            return await call_next(request)

        # Lazy-resolve MongoDB collection from app state on first real request
        if not self._col_resolved:
            try:
                db = getattr(request.app.state, "mongo_db", None)
                if db is not None:
                    self._col = db["request_metrics"]
                    self._col_resolved = True
            except Exception:
                self._col_resolved = True  # stop retrying

        start = time.monotonic()
        response = await call_next(request)
        latency_ms = (time.monotonic() - start) * 1_000

        endpoint = request.url.path
        status   = response.status_code

        # In-memory update (thread-safe)
        ts = time.time()
        with _lock:
            _buffer.append((ts, latency_ms, status, endpoint))
            _totals["requests"] += 1
            if status >= 400:
                _totals["errors"] += 1

        # MongoDB write — fire and forget (don't block the response)
        if self._col is not None:
            threading.Thread(
                target=self._write_mongo,
                args=(endpoint, request.method, status, latency_ms, ts, request),
                daemon=True,
            ).start()

        # Attach latency header so clients / load-balancers can observe it
        response.headers["X-Response-Time-ms"] = f"{latency_ms:.1f}"
        return response

    def _write_mongo(
        self,
        endpoint: str,
        method: str,
        status: int,
        latency_ms: float,
        ts: float,
        request: Request,
    ) -> None:
        try:
            client_ip = getattr(request.client, "host", "unknown")
            self._col.insert_one({
                "timestamp":  datetime.utcfromtimestamp(ts),
                "endpoint":   endpoint,
                "method":     method,
                "status":     status,
                "latency_ms": round(latency_ms, 2),
                "client_ip":  client_ip,
            })
        except Exception as e:
            logger.debug(f"Telemetry MongoDB write failed: {e}")
