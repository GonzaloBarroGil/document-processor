from abc import ABC, abstractmethod
from uuid import UUID

from document_processor.domain.models.document import Document, DocumentStatus
from document_processor.domain.models.parsed_data import ParsedData
from document_processor.domain.models.validation import ValidationResult


class DocumentRepositoryPort(ABC):
    @abstractmethod
    async def create(self, document: Document) -> Document:
        ...

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None:
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
        ...

    @abstractmethod
    async def update_status(
        self, document_id: UUID, status: DocumentStatus
    ) -> None:
        ...

    @abstractmethod
    async def update_parsed_data(
        self,
        document_id: UUID,
        parsed_data: ParsedData,
        validation_result: ValidationResult | None = None,
    ) -> None:
        ...

    @abstractmethod
    async def fetch_pending(
        self, worker_id: str, limit: int = 1
    ) -> list[Document]:
        ...

    @abstractmethod
    async def release_lock(self, document_id: UUID) -> None:
        ...
