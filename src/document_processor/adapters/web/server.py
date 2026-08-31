"""Production ASGI entry point.

Wires the real adapters (PostgreSQL, MinIO, OCR, regional validators) into the
FastAPI application and exposes it as ``app`` for ASGI servers, e.g.::

    uvicorn document_processor.adapters.web.server:app --host 0.0.0.0 --port 8000

The DB schema must be migrated first (``alembic upgrade head``) and PostgreSQL +
MinIO must be reachable before the app starts.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from document_processor.adapters.ocr.easyocr import EasyOCRAdapter
from document_processor.adapters.ocr.paddle import PaddleOCRAdapter
from document_processor.adapters.persistence.api_key_repo import PostgresApiKeyRepository
from document_processor.adapters.persistence.postgresql.audit_repository import (
    PostgresAuditRepository,
)
from document_processor.adapters.persistence.postgresql.daily_usage_repository import (
    PostgresDailyUsageRepository,
)
from document_processor.adapters.persistence.postgresql.failed_extraction_repository import (
    PostgresFailedExtractionRepository,
)
from document_processor.adapters.persistence.postgresql.refresh_token_repository import (
    PostgresRefreshTokenRepository,
)
from document_processor.adapters.persistence.postgresql.repository import (
    PostgresDocumentRepository,
)
from document_processor.adapters.persistence.postgresql.user_repository import (
    PostgresUserRepository,
)
from document_processor.adapters.storage.minio import MinioStorage
from document_processor.adapters.validators.registry import ValidatorRegistry
from document_processor.adapters.web.main import create_app
from document_processor.core.config import settings
from document_processor.domain.services.api_key_service import ApiKeyService
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.dashboard_service import DashboardService
from document_processor.domain.services.document_service import DocumentService
from document_processor.domain.services.export_service import ExportService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.quota_service import QuotaService
from document_processor.domain.services.review_service import ReviewService
from document_processor.domain.services.token_service import TokenService

_engine: AsyncEngine | None = None


def _build_ocr() -> PaddleOCRAdapter | EasyOCRAdapter:
    """Return the primary OCR adapter configured via settings."""
    if settings.ocr_primary_engine == "easyocr":
        return EasyOCRAdapter()
    return PaddleOCRAdapter()


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Dispose the shared engine on shutdown."""
    yield
    if _engine is not None:
        await _engine.dispose()


def build_app() -> FastAPI:
    """Build the fully-wired FastAPI application."""
    global _engine

    engine = create_async_engine(settings.database_url)
    _engine = engine
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    session = session_factory()

    validator_registry = ValidatorRegistry()
    validator_registry.discover()
    validators = dict(validator_registry._validators)

    document_repository = PostgresDocumentRepository(session)
    audit = PostgresAuditRepository(session)
    storage = MinioStorage()

    document_service = DocumentService(
        repository=document_repository,
        storage=storage,
        ocr=_build_ocr(),
        validator_registry=validators,
        audit=audit,
        failed_extraction=PostgresFailedExtractionRepository(session),
    )

    api_key_repository = PostgresApiKeyRepository(session)

    app = create_app(
        document_service=document_service,
        api_key_repository=api_key_repository,
        validator_registry=validators,
        auth_service=AuthService(
            user_repository=PostgresUserRepository(session),
            refresh_token_repository=PostgresRefreshTokenRepository(session),
            tokens=TokenService(),
            passwords=PasswordHasher(),
        ),
        review_service=ReviewService(repository=document_repository, audit=audit),
        export_service=ExportService(repository=document_repository),
        quota_service=QuotaService(PostgresDailyUsageRepository(session)),
        api_key_service=ApiKeyService(repository=api_key_repository),
        dashboard_service=DashboardService(repository=document_repository),
    )

    app.router.lifespan_context = _lifespan
    return app


app = build_app()
