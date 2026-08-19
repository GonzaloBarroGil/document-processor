from io import BytesIO

from minio import Minio
from minio.error import S3Error

from document_processor.core.config import settings
from document_processor.domain.ports.storage import StoragePort


class MinioStorage(StoragePort):
    """MinIO-backed implementation of the storage port."""

    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(settings.minio_bucket):
            self._client.make_bucket(settings.minio_bucket)

    async def store(self, key: str, data: bytes, content_type: str) -> None:
        """Store object bytes under the given key."""
        self._client.put_object(
            bucket_name=settings.minio_bucket,
            object_name=key,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    async def retrieve(self, key: str) -> bytes | None:
        """Return the object bytes for the given key, or None if absent."""
        try:
            response = self._client.get_object(
                bucket_name=settings.minio_bucket,
                object_name=key,
            )
            return response.read()
        except S3Error:
            return None

    async def delete(self, key: str) -> None:
        """Delete the object stored under the given key."""
        self._client.remove_object(
            bucket_name=settings.minio_bucket,
            object_name=key,
        )

    async def usage_pct(self) -> float:
        """Return storage usage as a percentage of the configured quota."""
        objects = self._client.list_objects(bucket_name=settings.minio_bucket, recursive=True)
        total_size = sum(int(obj.size or 0) for obj in objects)

        quota_bytes = 10 * 1024 * 1024 * 1024
        if total_size == 0:
            return 0.0
        return (float(total_size) / float(quota_bytes)) * 100.0
