from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str | float]:
    """Return service health and basic status."""
    return {
        "status": "ok",
        "ocr_engine": "paddle",
        "storage_pct": 0.0,
    }
