from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from document_processor.adapters.persistence.postgresql.models import (
    DocumentModel,
    document_to_model,
    model_to_document,
)
from document_processor.domain.models.document import Document, DocumentStatus
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult
from document_processor.domain.ports.document_repository import (
    DocumentRepositoryPort,
)


class PostgresDocumentRepository(DocumentRepositoryPort):
    """PostgreSQL-backed implementation of the document repository port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        """Persist a new document and return it."""
        model = document_to_model(document)
        self._session.add(model)
        await self._session.flush()
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Return the document with the given id, or None if absent."""
        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model_to_document(model)

    async def list_documents(
        self,
        status: DocumentStatus | None = None,
        type: str | None = None,
        region: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Document], int]:
        """Return a page of documents matching the given filters, plus the total count."""
        conditions = []
        if status:
            conditions.append(DocumentModel.status == status.value)
        if type:
            conditions.append(DocumentModel.type == type)
        if region:
            conditions.append(DocumentModel.region == region)

        count_stmt = select(func.count()).select_from(DocumentModel)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = select(DocumentModel).order_by(DocumentModel.created_at.desc())
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.offset((page - 1) * size).limit(size)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [model_to_document(m) for m in models], total

    async def update_status(self, document_id: UUID, status: DocumentStatus) -> None:
        """Update the status of the given document."""
        stmt = (
            update(DocumentModel)
            .where(DocumentModel.id == document_id)
            .values(status=status.value, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)

    async def update_parsed_data(
        self,
        document_id: UUID,
        parsed_data: ParsedData,
        validation_result: ValidationResult | None = None,
    ) -> None:
        """Update the parsed data and optional validation result of a document."""
        values = {
            "parsed_data": parsed_data.model_dump(mode="json"),
            "updated_at": datetime.now(UTC),
        }
        if validation_result:
            values["validation_result"] = validation_result.model_dump(mode="json")

        stmt = update(DocumentModel).where(DocumentModel.id == document_id).values(**values)
        await self._session.execute(stmt)

    async def fetch_pending(self, worker_id: str, limit: int = 1) -> list[Document]:
        """Return pending, unlocked documents ordered by creation time."""
        stmt = (
            select(DocumentModel)
            .where(
                DocumentModel.status == DocumentStatus.PENDING.value,
                DocumentModel.locked_by.is_(None),
            )
            .order_by(DocumentModel.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model_to_document(m) for m in models]

    async def release_lock(self, document_id: UUID) -> None:
        """Clear the lock held on the given document."""
        stmt = (
            update(DocumentModel)
            .where(DocumentModel.id == document_id)
            .values(locked_by=None, locked_at=None)
        )
        await self._session.execute(stmt)

    async def update_review(
        self,
        document_id: UUID,
        reviewed: bool,
        reviewed_by: UUID | None,
        reviewed_at: datetime | None,
        edited_fields: dict[str, str] | None,
        status: DocumentStatus | None = None,
    ) -> None:
        """Update the review state (and optional status) of the given document."""
        values: dict[str, object] = {
            "reviewed": reviewed,
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at,
            "edited_fields": edited_fields,
            "updated_at": datetime.now(UTC),
        }
        if status is not None:
            values["status"] = status.value

        stmt = update(DocumentModel).where(DocumentModel.id == document_id).values(**values)
        await self._session.execute(stmt)

    async def list_review_queue(self, page: int = 1, size: int = 20) -> tuple[list[Document], int]:
        """Return a page of documents awaiting review, plus the total count."""
        conditions = [
            DocumentModel.reviewed == False,  # noqa: E712
            DocumentModel.status.in_(
                [DocumentStatus.COMPLETED.value, DocumentStatus.VALIDATION_FAILED.value]
            ),
        ]

        count_stmt = select(func.count()).select_from(DocumentModel).where(*conditions)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(DocumentModel)
            .where(*conditions)
            .order_by(DocumentModel.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [model_to_document(m) for m in models], total

    async def count_by_status(self) -> dict[str, int]:
        """Return document counts grouped by status."""
        stmt = select(DocumentModel.status, func.count()).group_by(DocumentModel.status)
        result = await self._session.execute(stmt)
        counts: dict[str, int] = {}
        for status, count in result.all():
            counts[status] = count
        return counts
