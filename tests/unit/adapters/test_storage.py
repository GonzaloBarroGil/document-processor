from unittest.mock import MagicMock, patch

import pytest

from document_processor.adapters.storage.minio import MinioStorage


class TestMinioStorage:
    @pytest.fixture
    def storage(self) -> MinioStorage:
        with patch("document_processor.adapters.storage.minio.Minio") as mock_minio:
            mock_client = MagicMock()
            mock_client.bucket_exists.return_value = True
            mock_minio.return_value = mock_client
            s = MinioStorage()
            return s

    async def test_store(self, storage: MinioStorage) -> None:
        await storage.store("key.txt", b"data", "text/plain")
        storage._client.put_object.assert_called_once()

    async def test_retrieve_found(self, storage: MinioStorage) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"data"
        storage._client.get_object.return_value = mock_response

        result = await storage.retrieve("key.txt")
        assert result == b"data"

    async def test_retrieve_not_found(self, storage: MinioStorage) -> None:
        from minio.error import S3Error

        storage._client.get_object.side_effect = S3Error(
            "NoSuchKey", "", 404, "", "", ""
        )
        result = await storage.retrieve("missing.txt")
        assert result is None

    async def test_delete(self, storage: MinioStorage) -> None:
        await storage.delete("key.txt")
        storage._client.remove_object.assert_called_once()
