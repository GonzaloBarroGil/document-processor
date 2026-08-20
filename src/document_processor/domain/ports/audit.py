from abc import ABC, abstractmethod
from uuid import UUID

from document_processor.domain.models.audit import AuditAction


class AuditPort(ABC):
    """Port for recording immutable extraction audit entries."""

    @abstractmethod
    async def record(
        self,
        document_id: UUID,
        user_id: UUID | None,
        provider: str,
        confidence: float,
        action: AuditAction,
    ) -> None:
        """Append an immutable audit entry for the given document and action."""
        ...
