"""In-memory sliding-window rate limiter per user."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import get_settings

settings = get_settings()


class RateLimitStore:
    """Thread-safe sliding-window counter per user."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        with self._lock:
            timestamps = self._requests[key]
            timestamps[:] = [ts for ts in timestamps if now - ts < window_seconds]
            if len(timestamps) >= limit:
                return False
            timestamps.append(now)
            return True

    def remaining(self, key: str, limit: int, window_seconds: int = 60) -> int:
        now = time.monotonic()
        with self._lock:
            timestamps = self._requests[key]
            active = [ts for ts in timestamps if now - ts < window_seconds]
            return max(0, limit - len(active))


_store = RateLimitStore()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies per-user rate limiting to mutating API endpoints."""

    RATE_LIMITED_PREFIXES = ("/api/chat/", "/api/documents/upload")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        if not any(path.startswith(p) for p in self.RATE_LIMITED_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        key = auth_header[-16:] if auth_header else request.client.host if request.client else "anon"

        limit = settings.rate_limit_per_minute
        if not _store.is_allowed(key, limit):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {limit} requests per minute.",
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(_store.remaining(key, limit))
        return response
