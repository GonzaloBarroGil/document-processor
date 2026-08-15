from datetime import UTC, datetime
from uuid import uuid4

import pytest

from document_processor.domain.models.user import User, UserRole
from document_processor.domain.ports.auth import AuthPort


class TestUserRole:
    def test_role_values(self) -> None:
        roles = list(UserRole)
        assert UserRole.ADMIN in roles
        assert UserRole.REVIEWER in roles
        assert len(roles) == 2

    def test_role_string_values(self) -> None:
        assert UserRole.ADMIN.value == "ADMIN"
        assert UserRole.REVIEWER.value == "REVIEWER"


class TestUserModel:
    def test_create_user(self) -> None:
        user_id = uuid4()
        now = datetime.now(UTC)

        user = User(
            id=user_id,
            username="reviewer1",
            password_hash="argon2id-hash",
            role=UserRole.REVIEWER,
            created_at=now,
            updated_at=now,
        )

        assert user.id == user_id
        assert user.username == "reviewer1"
        assert user.password_hash == "argon2id-hash"
        assert user.role == UserRole.REVIEWER

    def test_default_role_is_reviewer(self) -> None:
        now = datetime.now(UTC)

        user = User(
            id=uuid4(),
            username="admin1",
            password_hash="argon2id-hash",
            created_at=now,
            updated_at=now,
        )

        assert user.role == UserRole.REVIEWER


class TestAuthPort:
    def test_auth_port_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AuthPort()  # type: ignore[abstract]
