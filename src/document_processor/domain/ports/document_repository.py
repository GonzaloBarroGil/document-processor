from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from document_processor.domain.models.document import Document, DocumentStatus
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult


class DocumentRepositoryPort(ABC):
    """Port for persisting and querying documents."""

    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Persist a new document and return it."""
        ...

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Return the document with the given id, or None if absent."""
        ...

    @abstractmethod
    async def list_documents(
        self,
        status: DocumentStatus | None = None,
        type: str | None = None,
        region: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Document], int]:
        """Return a filtered page of documents and the total count."""
        ...

    @abstractmethod
    async def update_status(self, document_id: UUID, status: DocumentStatus) -> None:
        """Update the status of the given document."""
        ...

    @abstractmethod
    async def update_parsed_data(
        self,
        document_id: UUID,
        parsed_data: ParsedData,
        validation_result: ValidationResult | None = None,
    ) -> None:
        """Update the parsed data and optional validation result of a document."""
        ...

    @abstractmethod
    async def fetch_pending(self, worker_id: str, limit: int = 1) -> list[Document]:
        """Return pending, unlocked documents for a worker to process."""
        ...

    @abstractmethod
    async def release_lock(self, document_id: UUID) -> None:
        """Release the lock held on the given document."""
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def list_review_queue(self, page: int = 1, size: int = 20) -> tuple[list[Document], int]:
        """Return a page of documents awaiting review, plus the total count."""
        ...

    @abstractmethod
    async def count_by_status(self) -> dict[str, int]:
        """Return document counts grouped by status."""
        ...
