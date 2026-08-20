from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from document_processor.adapters.persistence.postgresql.models import ExtractionAuditModel
from document_processor.domain.models.audit import AuditAction
from document_processor.domain.ports.audit import AuditPort


class PostgresAuditRepository(AuditPort):
    """PostgreSQL-backed implementation of the audit port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        document_id: UUID,
        user_id: UUID | None,
        provider: str,
        confidence: float,
        action: AuditAction,
    ) -> None:
        """Append an immutable audit entry for the given document and action."""
        model = ExtractionAuditModel(
            document_id=document_id,
            user_id=user_id,
            provider=provider,
            confidence=confidence,
            action=action.value,
        )
        self._session.add(model)
        await self._session.flush()
