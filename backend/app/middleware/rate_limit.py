"""
Sliding-window rate limiter implemented as a pure Starlette middleware.

No external dependencies — uses an in-memory dict.
Limits are keyed by (client_ip or api_key_prefix, route_prefix).

Configuration (via route_limits dict passed to __init__):
    {"/api/analyze": (10, 60), "/api/analyze/causal": (5, 60)}

means: 10 requests per 60 seconds on /api/analyze.
The GLOBAL fallback (default_limit) applies to all other routes.

Adds Retry-After and X-RateLimit-* headers to 429 responses.
"""

import hashlib
import json
import logging
import time
from collections import defaultdict, deque
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# (max_calls, window_seconds)
RateLimit = Tuple[int, int]


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        route_limits: Dict[str, RateLimit],
        default_limit: RateLimit = (60, 60),
    ):
        super().__init__(app)
        self.route_limits = route_limits   # path prefix → (calls, seconds)
        self.default_limit = default_limit
        # {identity_key: deque of request timestamps}
        self._windows: Dict[str, deque] = defaultdict(deque)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _identity(self, request: Request) -> str:
        """
        Rate-limit key: prefer API key hash (stable across IPs), fall back to IP.
        We use only the first 16 chars of the hash — enough to be unique, short
        enough that the key space stays manageable.
        """
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return "key:" + hashlib.sha256(api_key.encode()).hexdigest()[:16]
        host = getattr(request.client, "host", "unknown")
        return "ip:" + host

    def _get_limit(self, path: str) -> RateLimit:
        """Return the most specific matching limit for this path."""
        # Longest matching prefix wins
        match = ""
        for prefix in self.route_limits:
            if path.startswith(prefix) and len(prefix) > len(match):
                match = prefix
        return self.route_limits[match] if match else self.default_limit

    def _check(self, identity: str, path: str) -> Tuple[bool, int, int]:
        """
        Sliding-window check.

        Returns:
            (allowed, requests_remaining, retry_after_seconds)
        """
        max_calls, window = self._get_limit(path)
        now = time.monotonic()
        key = f"{identity}:{path.split('/')[1] if '/' in path else path}"

        window_start = now - window
        q = self._windows[key]

        # Drop timestamps outside the current window
        while q and q[0] < window_start:
            q.popleft()

        remaining = max_calls - len(q)
        if remaining <= 0:
            retry_after = int(window - (now - q[0])) + 1
            return False, 0, retry_after

        q.append(now)
        return True, remaining - 1, 0

    # ── middleware entrypoint ─────────────────────────────────────────────────

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip rate limiting for docs, health, root, and admin endpoints
        skip_prefixes = ("/docs", "/redoc", "/openapi.json", "/health", "/admin")
        if any(path.startswith(p) for p in skip_prefixes):
            return await call_next(request)

        identity = self._identity(request)
        allowed, remaining, retry_after = self._check(identity, path)

        if not allowed:
            logger.warning(f"Rate limit hit: {identity} on {path}")
            body = json.dumps({
                "detail": f"Rate limit exceeded. Retry after {retry_after} seconds.",
                "retry_after": retry_after,
            })
            return Response(
                content=body,
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
