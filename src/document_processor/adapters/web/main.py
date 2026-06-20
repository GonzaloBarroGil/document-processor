from contextlib import asynccontextmanager

from fastapi import FastAPI

from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.ports.api_key_repository import ApiKeyRepositoryPort
from document_processor.domain.ports.region_validator import RegionValidatorPort
from document_processor.adapters.web.api import documents, health
from document_processor.adapters.web.api.deps import set_document_service
from document_processor.adapters.web.middleware.auth import AuthMiddleware
from document_processor.adapters.web.middleware.rate_limit import RateLimitMiddleware


def create_app(
    document_service: DocumentService,
    api_key_repository: ApiKeyRepositoryPort,
    validator_registry: dict[str, RegionValidatorPort],
) -> FastAPI:
    set_document_service(document_service)

    app = FastAPI(title="Document Processor", version="0.1.0")

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware, api_key_repository=api_key_repository)

    app.include_router(documents.router)
    app.include_router(health.router)

    return app
