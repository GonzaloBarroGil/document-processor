import pytest


@pytest.mark.skip(reason="Requires Docker: PostgreSQL + MinIO running")
class TestWorkerEndToEnd:
    async def test_full_pipeline_ingest_to_complete(self) -> None:
        pass

    async def test_ocr_failure_sets_status(self) -> None:
        pass

    async def test_worker_handles_concurrent_documents(self) -> None:
        pass

    async def test_worker_graceful_shutdown(self) -> None:
        pass
