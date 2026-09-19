import time
import logging
from collections import defaultdict
from threading import Lock
from typing import Dict, List
from fastapi import Request, HTTPException, status

from app.core.config import settings

logger = logging.getLogger("devforge.rate_limit")


class SlidingWindowRateLimiter:
    """
    Thread-safe, sliding-window rate limiter by client IP and action scope.
    """

    def __init__(self):
        # key: (client_ip, scope) -> list of timestamp floats
        self._history: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def check(
        self,
        request: Request,
        scope: str,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> None:
        """
        Check rate limit. If exceeded, raises HTTP 429 with Retry-After header.
        """
        if not settings.RATE_LIMIT_ENABLED:
            return

        client_ip = self._get_client_ip(request)
        key = f"{client_ip}:{scope}"
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            # Filter timestamps to current window
            timestamps = [ts for ts in self._history[key] if ts > window_start]
            if len(timestamps) >= max_requests:
                oldest = timestamps[0]
                retry_after = max(1, int(window_seconds - (now - oldest)))
                logger.warning(
                    f"Rate limit exceeded for client {client_ip} on scope '{scope}' "
                    f"({len(timestamps)}/{max_requests} reqs in {window_seconds}s). Retry after {retry_after}s."
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests for '{scope}'. Rate limit exceeded ({max_requests} requests per {window_seconds} seconds).",
                    headers={"Retry-After": str(retry_after)}
                )

            timestamps.append(now)
            self._history[key] = timestamps

    def reset(self):
        """Clear all rate limit history (useful for test isolation)."""
        with self._lock:
            self._history.clear()


rate_limiter = SlidingWindowRateLimiter()


def rate_limit(scope: str, max_requests: int = 10, window_seconds: int = 60):
    """
    FastAPI dependency factory to enforce rate limiting on specific endpoints.
    """
    async def dependency(request: Request):
        rate_limiter.check(request, scope=scope, max_requests=max_requests, window_seconds=window_seconds)

    return dependency
