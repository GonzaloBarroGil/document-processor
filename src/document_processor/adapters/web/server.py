"""Production ASGI entry point.

Wires the real adapters (PostgreSQL, MinIO, OCR, regional validators) into the
FastAPI application and exposes it as ``app`` for ASGI servers, e.g.::

    uvicorn document_processor.adapters.web.server:app --host 0.0.0.0 --port 8000

The DB schema must be migrated first (``alembic upgrade head``) and PostgreSQL +
MinIO must be reachable before the app starts.

Concurrency model: each request gets its own ``AsyncSession`` (``_get_db``), shared
across the services resolved for that request and committed once at the end. Stateless
collaborators (OCR engine, validator registry, storage, token/password services) are
built once and shared. The auth middleware validates API keys on its own short-lived
session (``SessionScopedApiKeyRepository``), since it runs before the request-scoped
session exists.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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
from document_processor.adapters.web.api.deps import (
    get_api_key_service,
    get_auth_service,
    get_dashboard_service,
    get_document_service,
    get_export_service,
    get_optional_auth_service,
    get_quota_service,
    get_review_service,
)
from document_processor.adapters.web.main import create_app
from document_processor.core.config import settings
from document_processor.domain.models.api_key import ApiKey
from document_processor.domain.ports.api_key_repository import ApiKeyRepositoryPort
from document_processor.domain.ports.ocr import OCRPort
from document_processor.domain.ports.region_validator import RegionValidatorPort
from document_processor.domain.ports.storage import StoragePort
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


@dataclass
class ServiceContext:
    """Stateless collaborators shared across requests, plus the session factory."""

    session_factory: async_sessionmaker[AsyncSession]
    ocr: OCRPort
    validators: dict[str, RegionValidatorPort]
    storage: StoragePort
    tokens: TokenService
    passwords: PasswordHasher


class SessionScopedApiKeyRepository(ApiKeyRepositoryPort):
    """ApiKeyRepositoryPort that opens a short-lived session per operation.

    Used by the auth middleware, which validates API keys before the request-scoped
    ``get_db`` session is available.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def validate_key(self, key_hash: str) -> bool:
        """Return whether the given key hash identifies an active API key."""
        async with self._factory() as session:
            return await PostgresApiKeyRepository(session).validate_key(key_hash)

    async def create(self, api_key: ApiKey) -> ApiKey:
        """Persist and return a newly created API key."""
        async with self._factory() as session:
            result = await PostgresApiKeyRepository(session).create(api_key)
            await session.commit()
            return result

    async def list_keys(self) -> list[ApiKey]:
        """Return all API keys, most recent first."""
        async with self._factory() as session:
            return await PostgresApiKeyRepository(session).list_keys()

    async def revoke(self, prefix: str) -> bool:
        """Revoke the API key with the given prefix; return whether one was revoked."""
        async with self._factory() as session:
            result = await PostgresApiKeyRepository(session).revoke(prefix)
            await session.commit()
            return result


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


async def _get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session, committing on success and rolling back on error."""
    session_factory = request.app.state.service_context.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _request_document_service(
    request: Request,
    session: AsyncSession = Depends(_get_db),  # noqa: B008
) -> DocumentService:
    context = request.app.state.service_context
    return DocumentService(
        repository=PostgresDocumentRepository(session),
        storage=context.storage,
        ocr=context.ocr,
        validator_registry=context.validators,
        audit=PostgresAuditRepository(session),
        failed_extraction=PostgresFailedExtractionRepository(session),
    )


def _request_auth_service(
    request: Request,
    session: AsyncSession = Depends(_get_db),  # noqa: B008
) -> AuthService:
    context = request.app.state.service_context
    return AuthService(
        user_repository=PostgresUserRepository(session),
        refresh_token_repository=PostgresRefreshTokenRepository(session),
        tokens=context.tokens,
        passwords=context.passwords,
    )


def _request_review_service(
    request: Request,
    session: AsyncSession = Depends(_get_db),  # noqa: B008
) -> ReviewService:
    return ReviewService(
        repository=PostgresDocumentRepository(session),
        audit=PostgresAuditRepository(session),
    )


def _request_export_service(
    request: Request,
    session: AsyncSession = Depends(_get_db),  # noqa: B008
) -> ExportService:
    return ExportService(repository=PostgresDocumentRepository(session))


def _request_quota_service(
    request: Request,
    session: AsyncSession = Depends(_get_db),  # noqa: B008
) -> QuotaService:
    return QuotaService(PostgresDailyUsageRepository(session))


def _request_api_key_service(
    request: Request,
    session: AsyncSession = Depends(_get_db),  # noqa: B008
) -> ApiKeyService:
    return ApiKeyService(repository=PostgresApiKeyRepository(session))


def _request_dashboard_service(
    request: Request,
    session: AsyncSession = Depends(_get_db),  # noqa: B008
) -> DashboardService:
    return DashboardService(repository=PostgresDocumentRepository(session))


def build_app() -> FastAPI:
    """Build the fully-wired FastAPI application."""
    global _engine

    engine = create_async_engine(settings.database_url)
    _engine = engine
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    validator_registry = ValidatorRegistry()
    validator_registry.discover()

    context = ServiceContext(
        session_factory=session_factory,
        ocr=_build_ocr(),
        validators=dict(validator_registry._validators),
        storage=MinioStorage(),
        tokens=TokenService(),
        passwords=PasswordHasher(),
    )

    app = create_app(
        api_key_repository=SessionScopedApiKeyRepository(session_factory),
        include_all_routers=True,
    )
    app.state.service_context = context

    app.dependency_overrides[get_document_service] = _request_document_service
    app.dependency_overrides[get_auth_service] = _request_auth_service
    app.dependency_overrides[get_optional_auth_service] = _request_auth_service
    app.dependency_overrides[get_review_service] = _request_review_service
    app.dependency_overrides[get_export_service] = _request_export_service
    app.dependency_overrides[get_quota_service] = _request_quota_service
    app.dependency_overrides[get_api_key_service] = _request_api_key_service
    app.dependency_overrides[get_dashboard_service] = _request_dashboard_service

    app.router.lifespan_context = _lifespan
    return app


app = build_app()
