"""Unit tests for the production ASGI wiring in ``server.py``."""

import importlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SERVER = "document_processor.adapters.web.server"


class _FakeSession:
    """A minimal stand-in for an ``AsyncSession``."""

    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.rollback = AsyncMock()


class _FakeSessionFactory:
    """Callable returning an async context manager that yields a fixed session."""

    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    def __call__(self):
        @asynccontextmanager
        async def _cm():
            yield self._session

        return _cm()


def _fake_request(context):
    request = MagicMock()
    request.app.state.service_context = context
    return request


def _context(server):
    return server.ServiceContext(
        session_factory=MagicMock(),
        ocr=MagicMock(),
        validators={},
        storage=MagicMock(),
        tokens=MagicMock(),
        passwords=MagicMock(),
    )


@pytest.fixture(scope="module")
def server():
    """Import the server module with the network-touching MinIO client mocked."""
    with patch("document_processor.adapters.storage.minio.MinioStorage") as mock_storage:
        mock_storage.return_value = MagicMock(name="storage")
        yield importlib.import_module(SERVER)


class TestBuildApp:
    def test_app_is_fastapi(self, server) -> None:
        assert isinstance(server.app, server.FastAPI)

    def test_service_context_is_wired(self, server) -> None:
        assert isinstance(server.app.state.service_context, server.ServiceContext)

    def test_dependency_overrides(self, server) -> None:
        overrides = server.app.dependency_overrides
        assert len(overrides) == 8
        assert overrides[server.get_document_service] is server._request_document_service
        assert overrides[server.get_auth_service] is server._request_auth_service
        assert overrides[server.get_optional_auth_service] is server._request_auth_service
        assert overrides[server.get_review_service] is server._request_review_service
        assert overrides[server.get_export_service] is server._request_export_service
        assert overrides[server.get_quota_service] is server._request_quota_service
        assert overrides[server.get_api_key_service] is server._request_api_key_service
        assert overrides[server.get_dashboard_service] is server._request_dashboard_service

    def test_lifespan_context(self, server) -> None:
        assert server.app.router.lifespan_context is server._lifespan


class TestBuildOcr:
    def test_easyocr(self, server, monkeypatch) -> None:
        monkeypatch.setattr(server.settings, "ocr_primary_engine", "easyocr")
        assert isinstance(server._build_ocr(), server.EasyOCRAdapter)

    def test_paddle_default(self, server, monkeypatch) -> None:
        monkeypatch.setattr(server.settings, "ocr_primary_engine", "paddle")
        assert isinstance(server._build_ocr(), server.PaddleOCRAdapter)


class TestLifespan:
    async def test_disposes_engine(self, server) -> None:
        engine = MagicMock()
        engine.dispose = AsyncMock()
        server._engine = engine
        async with server._lifespan(None):
            pass
        engine.dispose.assert_awaited_once()

    async def test_noop_without_engine(self, server) -> None:
        server._engine = None
        async with server._lifespan(None):
            pass


class TestGetDb:
    async def test_commits_on_success(self, server) -> None:
        session = _FakeSession()
        context = server.ServiceContext(
            session_factory=_FakeSessionFactory(session),
            ocr=MagicMock(),
            validators={},
            storage=MagicMock(),
            tokens=MagicMock(),
            passwords=MagicMock(),
        )
        gen = server._get_db(_fake_request(context))
        yielded = await gen.__anext__()
        assert yielded is session
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()

    async def test_rolls_back_on_error(self, server) -> None:
        session = _FakeSession()
        session.commit = AsyncMock(side_effect=RuntimeError("boom"))
        context = server.ServiceContext(
            session_factory=_FakeSessionFactory(session),
            ocr=MagicMock(),
            validators={},
            storage=MagicMock(),
            tokens=MagicMock(),
            passwords=MagicMock(),
        )
        gen = server._get_db(_fake_request(context))
        await gen.__anext__()
        with pytest.raises(RuntimeError):
            await gen.__anext__()
        session.rollback.assert_awaited_once()


class TestSessionScopedApiKeyRepository:
    def _patch_repo(self, server, monkeypatch):
        repo = MagicMock()
        monkeypatch.setattr(server, "PostgresApiKeyRepository", MagicMock(return_value=repo))
        return repo

    async def test_validate_key(self, server, monkeypatch) -> None:
        repo = self._patch_repo(server, monkeypatch)
        repo.validate_key = AsyncMock(return_value=True)
        session = _FakeSession()
        wrapper = server.SessionScopedApiKeyRepository(_FakeSessionFactory(session))
        assert await wrapper.validate_key("hash") is True
        server.PostgresApiKeyRepository.assert_called_once_with(session)

    async def test_create_commits(self, server, monkeypatch) -> None:
        repo = self._patch_repo(server, monkeypatch)
        repo.create = AsyncMock(return_value="key")
        session = _FakeSession()
        wrapper = server.SessionScopedApiKeyRepository(_FakeSessionFactory(session))
        api_key = MagicMock()
        assert await wrapper.create(api_key) == "key"
        session.commit.assert_awaited_once()

    async def test_list_keys(self, server, monkeypatch) -> None:
        repo = self._patch_repo(server, monkeypatch)
        repo.list_keys = AsyncMock(return_value=["a", "b"])
        session = _FakeSession()
        wrapper = server.SessionScopedApiKeyRepository(_FakeSessionFactory(session))
        assert await wrapper.list_keys() == ["a", "b"]
        session.commit.assert_not_awaited()

    async def test_revoke_commits(self, server, monkeypatch) -> None:
        repo = self._patch_repo(server, monkeypatch)
        repo.revoke = AsyncMock(return_value=True)
        session = _FakeSession()
        wrapper = server.SessionScopedApiKeyRepository(_FakeSessionFactory(session))
        assert await wrapper.revoke("prefix") is True
        session.commit.assert_awaited_once()


class TestRequestFactories:
    async def test_document_service(self, server) -> None:
        session = MagicMock()
        context = _context(server)
        result = server._request_document_service(_fake_request(context), session)
        assert isinstance(result, server.DocumentService)
        assert isinstance(result._repository, server.PostgresDocumentRepository)
        assert result._storage is context.storage
        assert result._ocr is context.ocr
        assert result._validator_registry is context.validators
        assert isinstance(result._audit, server.PostgresAuditRepository)
        assert isinstance(result._failed_extraction, server.PostgresFailedExtractionRepository)

    async def test_auth_service(self, server) -> None:
        session = MagicMock()
        context = _context(server)
        result = server._request_auth_service(_fake_request(context), session)
        assert isinstance(result, server.AuthService)
        assert isinstance(result._user_repository, server.PostgresUserRepository)
        assert isinstance(result._refresh_token_repository, server.PostgresRefreshTokenRepository)
        assert result._tokens is context.tokens
        assert result._passwords is context.passwords

    async def test_review_service(self, server) -> None:
        session = MagicMock()
        result = server._request_review_service(_fake_request(_context(server)), session)
        assert isinstance(result, server.ReviewService)
        assert isinstance(result._repository, server.PostgresDocumentRepository)
        assert isinstance(result._audit, server.PostgresAuditRepository)

    async def test_export_service(self, server) -> None:
        session = MagicMock()
        result = server._request_export_service(_fake_request(_context(server)), session)
        assert isinstance(result, server.ExportService)
        assert isinstance(result._repository, server.PostgresDocumentRepository)

    async def test_quota_service(self, server) -> None:
        session = MagicMock()
        result = server._request_quota_service(_fake_request(_context(server)), session)
        assert isinstance(result, server.QuotaService)
        assert isinstance(result._usage_repository, server.PostgresDailyUsageRepository)

    async def test_api_key_service(self, server) -> None:
        session = MagicMock()
        result = server._request_api_key_service(_fake_request(_context(server)), session)
        assert isinstance(result, server.ApiKeyService)
        assert isinstance(result._repository, server.PostgresApiKeyRepository)

    async def test_dashboard_service(self, server) -> None:
        session = MagicMock()
        result = server._request_dashboard_service(_fake_request(_context(server)), session)
        assert isinstance(result, server.DashboardService)
        assert isinstance(result._repository, server.PostgresDocumentRepository)
