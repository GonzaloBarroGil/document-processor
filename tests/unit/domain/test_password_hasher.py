import pytest

from document_processor.domain.services.password_hasher import PasswordHasher


class TestPasswordHasher:
    @pytest.fixture
    def hasher(self) -> PasswordHasher:
        return PasswordHasher()

    def test_hash_uses_argon2id(self, hasher: PasswordHasher) -> None:
        digest = hasher.hash("s3cret")
        assert digest.startswith("$argon2id$")

    def test_verify_correct_password(self, hasher: PasswordHasher) -> None:
        digest = hasher.hash("s3cret")
        assert hasher.verify("s3cret", digest)

    def test_verify_wrong_password(self, hasher: PasswordHasher) -> None:
        digest = hasher.hash("s3cret")
        assert not hasher.verify("wrong", digest)

    def test_verify_malformed_hash_returns_false(self, hasher: PasswordHasher) -> None:
        assert not hasher.verify("s3cret", "not-a-real-hash")
