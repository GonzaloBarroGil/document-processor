from fastapi import APIRouter, Depends

from document_processor.adapters.web.api.deps import (
    get_dashboard_service,
    require_reviewer,
)
from document_processor.domain.models.dashboard import DashboardSummary
from document_processor.domain.models.user import User
from document_processor.domain.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardSummary)
async def dashboard(
    user: User = Depends(require_reviewer),  # noqa: B008
    service: DashboardService = Depends(get_dashboard_service),  # noqa: B008
) -> DashboardSummary:
    """Return the processing summary for the dashboard."""
    return await service.summary()
