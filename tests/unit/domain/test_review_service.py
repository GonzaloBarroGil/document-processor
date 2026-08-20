from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from document_processor.core.errors import DocumentNotFoundError
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
    ReviewAction,
)
from document_processor.domain.services.review_service import ReviewService


def _make_document() -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid4(),
        type=DocumentType.INVOICE,
        region="AR",
        status=DocumentStatus.VALIDATION_FAILED,
        media_type=MediaType.JPEG,
        image_key="img.jpg",
        created_at=now,
        updated_at=now,
    )


class TestReviewService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, repo: MagicMock) -> ReviewService:
        return ReviewService(repository=repo)

    async def test_approve_marks_reviewed(self, service: ReviewService, repo: MagicMock) -> None:
        doc = _make_document()
        reviewer_id = uuid4()
        repo.get_by_id = AsyncMock(side_effect=[doc, doc])
        repo.update_review = AsyncMock()

        result = await service.review(doc.id, reviewer_id, ReviewAction.APPROVE, {"total": "1500"})

        repo.update_review.assert_called_once()
        call = repo.update_review.call_args
        assert call.kwargs["reviewed"] is True
        assert call.kwargs["reviewed_by"] == reviewer_id
        assert call.kwargs["status"] == DocumentStatus.COMPLETED
        assert call.kwargs["edited_fields"] == {"total": "1500"}
        assert result.id == doc.id

    async def test_reject_marks_failed(self, service: ReviewService, repo: MagicMock) -> None:
        doc = _make_document()
        repo.get_by_id = AsyncMock(side_effect=[doc, doc])
        repo.update_review = AsyncMock()

        await service.review(doc.id, uuid4(), ReviewAction.REJECT)

        call = repo.update_review.call_args
        assert call.kwargs["reviewed"] is True
        assert call.kwargs["status"] == DocumentStatus.VALIDATION_FAILED

    async def test_request_changes_requeues(self, service: ReviewService, repo: MagicMock) -> None:
        doc = _make_document()
        repo.get_by_id = AsyncMock(side_effect=[doc, doc])
        repo.update_review = AsyncMock()

        await service.review(doc.id, uuid4(), ReviewAction.REQUEST_CHANGES)

        call = repo.update_review.call_args
        assert call.kwargs["reviewed"] is False
        assert call.kwargs["status"] == DocumentStatus.PENDING

    async def test_review_not_found(self, service: ReviewService, repo: MagicMock) -> None:
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(DocumentNotFoundError):
            await service.review(uuid4(), uuid4(), ReviewAction.APPROVE)

    async def test_list_review_queue(self, service: ReviewService, repo: MagicMock) -> None:
        repo.list_review_queue = AsyncMock(return_value=([], 0))

        docs, total = await service.list_review_queue(page=1, size=10)

        assert docs == []
        assert total == 0
