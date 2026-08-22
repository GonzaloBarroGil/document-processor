from pydantic import BaseModel

from document_processor.domain.models.document import Document


class DashboardSummary(BaseModel):
    """A processing summary for the dashboard."""

    counts: dict[str, int]
    recent: list[Document]
