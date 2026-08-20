from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import Depends, FastAPI
from starlette.testclient import TestClient

from document_processor.adapters.web.api.deps import require_admin, set_auth_service
from document_processor.domain.models.user import User, UserRole
from document_processor.domain.services.auth_service import AuthService
from document_processor.domain.services.password_hasher import PasswordHasher
from document_processor.domain.services.token_service import TokenService


def _make_user(role: UserRole) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        username="alice",
        password_hash="hash",
        role=role,
        created_at=now,
        updated_at=now,
    )


def _build_client(role: UserRole) -> tuple[TestClient, User]:
    user = _make_user(role)

    user_repo = MagicMock()
    user_repo.get_user_by_id = AsyncMock(return_value=user)
    user_repo.get_user_by_username = AsyncMock(return_value=user)
    refresh_repo = MagicMock()
    refresh_repo.save = AsyncMock()
    refresh_repo.is_active = AsyncMock(return_value=True)
    refresh_repo.revoke = AsyncMock()

    auth_service = AuthService(
        user_repository=user_repo,
        refresh_token_repository=refresh_repo,
        tokens=TokenService(),
        passwords=PasswordHasher(),
    )
    set_auth_service(auth_service)

    app = FastAPI()

    @app.get("/admin-only")
    async def admin_only(_: User = Depends(require_admin)) -> dict[str, str]:  # noqa: B008
        return {"ok": "admin"}

    return TestClient(app), user


class TestRbacIntegration:
    def test_admin_can_access(self) -> None:
        client, user = _build_client(UserRole.ADMIN)
        token = TokenService().issue_access_token(user.id, user.role)

        response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200

    def test_reviewer_is_forbidden(self) -> None:
        client, user = _build_client(UserRole.REVIEWER)
        token = TokenService().issue_access_token(user.id, user.role)

        response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 403
