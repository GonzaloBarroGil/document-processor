from datetime import UTC, datetime
from uuid import UUID

from document_processor.core.errors import DocumentNotFoundError
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    ReviewAction,
)
from document_processor.domain.ports.document_repository import (
    DocumentRepositoryPort,
)


class ReviewService:
    """Applies human review decisions to documents."""

    def __init__(self, repository: DocumentRepositoryPort) -> None:
        self._repository = repository

    async def review(
        self,
        document_id: UUID,
        reviewer_id: UUID,
        action: ReviewAction,
        edited_fields: dict[str, str] | None = None,
    ) -> Document:
        """Apply a review decision and return the updated document."""
        document = await self._repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(str(document_id))

        reviewed_at = datetime.now(UTC)

        if action == ReviewAction.APPROVE:
            await self._repository.update_review(
                document_id=document_id,
                reviewed=True,
                reviewed_by=reviewer_id,
                reviewed_at=reviewed_at,
                edited_fields=edited_fields,
                status=DocumentStatus.COMPLETED,
            )
        elif action == ReviewAction.REJECT:
            await self._repository.update_review(
                document_id=document_id,
                reviewed=True,
                reviewed_by=reviewer_id,
                reviewed_at=reviewed_at,
                edited_fields=None,
                status=DocumentStatus.VALIDATION_FAILED,
            )
        else:
            await self._repository.update_review(
                document_id=document_id,
                reviewed=False,
                reviewed_by=reviewer_id,
                reviewed_at=reviewed_at,
                edited_fields=edited_fields,
                status=DocumentStatus.PENDING,
            )

        updated = await self._repository.get_by_id(document_id)
        assert updated is not None
        return updated

    async def list_review_queue(self, page: int = 1, size: int = 20) -> tuple[list[Document], int]:
        """Return a page of documents awaiting review, plus the total count."""
        return await self._repository.list_review_queue(page=page, size=size)
