import hashlib
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from document_processor.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._windows: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.method != "POST":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "anonymous")
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        now = time.time()
        window_start = now - settings.rate_limit_window_seconds

        self._windows[key_hash] = [
            ts for ts in self._windows[key_hash] if ts > window_start
        ]

        if len(self._windows[key_hash]) >= settings.rate_limit_per_minute:
            oldest = min(self._windows[key_hash])
            retry_after = int(oldest + settings.rate_limit_window_seconds - now + 1)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        self._windows[key_hash].append(now)
        return await call_next(request)
