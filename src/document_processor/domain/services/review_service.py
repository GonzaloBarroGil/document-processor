from datetime import UTC, datetime
from uuid import UUID

from document_processor.core.errors import DocumentNotFoundError
from document_processor.domain.models.audit import AuditAction
from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    ReviewAction,
)
from document_processor.domain.ports.audit import AuditPort
from document_processor.domain.ports.document_repository import (
    DocumentRepositoryPort,
)


class ReviewService:
    """Applies human review decisions to documents."""

    def __init__(
        self,
        repository: DocumentRepositoryPort,
        audit: AuditPort | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit

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
            audit_action = AuditAction.REVIEW_APPROVE
        elif action == ReviewAction.REJECT:
            await self._repository.update_review(
                document_id=document_id,
                reviewed=True,
                reviewed_by=reviewer_id,
                reviewed_at=reviewed_at,
                edited_fields=None,
                status=DocumentStatus.VALIDATION_FAILED,
            )
            audit_action = AuditAction.REVIEW_REJECT
        else:
            await self._repository.update_review(
                document_id=document_id,
                reviewed=False,
                reviewed_by=reviewer_id,
                reviewed_at=reviewed_at,
                edited_fields=edited_fields,
                status=DocumentStatus.PENDING,
            )
            audit_action = AuditAction.REVIEW_REQUEST_CHANGES

        if self._audit is not None:
            await self._audit.record(
                document_id=document_id,
                user_id=reviewer_id,
                provider="human",
                confidence=0.0,
                action=audit_action,
            )

        updated = await self._repository.get_by_id(document_id)
        assert updated is not None
        return updated

    async def list_review_queue(self, page: int = 1, size: int = 20) -> tuple[list[Document], int]:
        """Return a page of documents awaiting review, plus the total count."""
        return await self._repository.list_review_queue(page=page, size=size)
