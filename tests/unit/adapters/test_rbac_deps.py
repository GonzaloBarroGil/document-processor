from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from document_processor.adapters.web.api.deps import (
    require_admin,
    require_reviewer,
    require_roles,
)
from document_processor.domain.models.user import User, UserRole


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


class TestRequireRoles:
    async def test_require_roles_allows_matching_role(self) -> None:
        guard = require_roles(UserRole.REVIEWER)
        user = _make_user(UserRole.REVIEWER)

        result = await guard(user=user)

        assert result is user

    async def test_require_roles_rejects_other_role(self) -> None:
        guard = require_roles(UserRole.ADMIN)
        user = _make_user(UserRole.REVIEWER)

        with pytest.raises(HTTPException) as exc:
            await guard(user=user)

        assert exc.value.status_code == 403
        assert exc.value.detail == "Insufficient role"


class TestRequireAdmin:
    async def test_allows_admin(self) -> None:
        user = _make_user(UserRole.ADMIN)

        result = await require_admin(user=user)

        assert result is user

    async def test_rejects_reviewer(self) -> None:
        user = _make_user(UserRole.REVIEWER)

        with pytest.raises(HTTPException) as exc:
            await require_admin(user=user)

        assert exc.value.status_code == 403


class TestRequireReviewer:
    async def test_allows_admin(self) -> None:
        user = _make_user(UserRole.ADMIN)

        result = await require_reviewer(user=user)

        assert result is user

    async def test_allows_reviewer(self) -> None:
        user = _make_user(UserRole.REVIEWER)

        result = await require_reviewer(user=user)

        assert result is user
