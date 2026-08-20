from fastapi import FastAPI

from document_processor.adapters.web.api import auth, documents, health, review
from document_processor.adapters.web.api.deps import (
    set_auth_service,
    set_document_service,
    set_review_service,
)
from document_processor.adapters.web.middleware.auth import AuthMiddleware
from document_processor.adapters.web.middleware.rate_limit import RateLimitMiddleware
from document_processor.domain.ports.api_key_repository import ApiKeyRepositoryPort
from document_processor.domain.ports.region_validator import RegionValidatorPort
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.review_service import ReviewService


def create_app(
    document_service: DocumentService,
    api_key_repository: ApiKeyRepositoryPort,
    validator_registry: dict[str, RegionValidatorPort],
    auth_service: AuthService | None = None,
    review_service: ReviewService | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    set_document_service(document_service)

    app = FastAPI(title="Document Processor", version="0.1.0")

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware, api_key_repository=api_key_repository)

    app.include_router(documents.router)
    app.include_router(health.router)

    if auth_service is not None:
        set_auth_service(auth_service)
        app.include_router(auth.router)

    if review_service is not None:
        set_review_service(review_service)
        app.include_router(review.router)

    return app
