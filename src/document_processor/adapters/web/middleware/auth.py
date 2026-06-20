import hashlib

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from document_processor.domain.ports.api_key_repository import ApiKeyRepositoryPort


class AuthMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {"/api/v1/health", "/openapi.json", "/docs", "/redoc"}

    def __init__(self, app, api_key_repository: ApiKeyRepositoryPort) -> None:
        super().__init__(app)
        self._api_key_repository = api_key_repository

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if api_key is None:
            return JSONResponse(
                status_code=401, content={"detail": "Missing X-API-Key header"}
            )

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        valid = await self._api_key_repository.validate_key(key_hash)

        if not valid:
            return JSONResponse(
                status_code=403, content={"detail": "Invalid or revoked API key"}
            )

        return await call_next(request)
