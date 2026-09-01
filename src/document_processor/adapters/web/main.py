from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from document_processor.adapters.web.api import (
    api_keys,
    auth,
    dashboard,
    documents,
    export,
    health,
    review,
)
from document_processor.adapters.web.api.deps import (
    set_api_key_service,
    set_auth_service,
    set_dashboard_service,
    set_document_service,
    set_export_service,
    set_quota_service,
    set_review_service,
)
from document_processor.adapters.web.middleware.auth import AuthMiddleware
from document_processor.adapters.web.middleware.rate_limit import RateLimitMiddleware
from document_processor.core.config import settings
from document_processor.domain.ports.api_key_repository import ApiKeyRepositoryPort
from document_processor.domain.ports.region_validator import RegionValidatorPort
from document_processor.domain.services.api_key_service import ApiKeyService
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.dashboard_service import DashboardService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.export_service import ExportService
from document_processor.domain.services.quota_service import QuotaService
from document_processor.domain.services.review_service import ReviewService


def create_app(
    document_service: DocumentService | None = None,
    api_key_repository: ApiKeyRepositoryPort | None = None,
    validator_registry: dict[str, RegionValidatorPort] | None = None,
    auth_service: AuthService | None = None,
    review_service: ReviewService | None = None,
    export_service: ExportService | None = None,
    quota_service: QuotaService | None = None,
    api_key_service: ApiKeyService | None = None,
    dashboard_service: DashboardService | None = None,
    include_all_routers: bool = False,
) -> FastAPI:
    """Create and configure the FastAPI application.

    ``document_service`` / ``api_key_repository`` / ``validator_registry`` are retained as
    keywords for the test suites, which inject mocks and rely on the module-level singletons in
    ``deps.py``. Production uses ``include_all_routers=True`` with ``None`` services and installs
    request-scoped dependency overrides in ``server.py``.
    """
    if document_service is not None:
        set_document_service(document_service)

    app = FastAPI(title="Document Processor", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    if api_key_repository is not None:
        app.add_middleware(AuthMiddleware, api_key_repository=api_key_repository)

    app.include_router(documents.router)
    app.include_router(health.router)

    if include_all_routers or auth_service is not None:
        app.include_router(auth.router)

    if include_all_routers or review_service is not None:
        app.include_router(review.router)

    if include_all_routers or export_service is not None:
        app.include_router(export.router)

    if include_all_routers or api_key_service is not None:
        app.include_router(api_keys.router)

    if include_all_routers or dashboard_service is not None:
        app.include_router(dashboard.router)

    if auth_service is not None:
        set_auth_service(auth_service)

    if review_service is not None:
        set_review_service(review_service)

    if export_service is not None:
        set_export_service(export_service)

    if api_key_service is not None:
        set_api_key_service(api_key_service)

    if dashboard_service is not None:
        set_dashboard_service(dashboard_service)

    set_quota_service(quota_service)

    return app
