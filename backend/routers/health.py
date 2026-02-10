"""Health check routes."""
from fastapi import APIRouter

from database import check_db_connection
from schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check including database connectivity."""
    db_ok = await check_db_connection()
    return HealthResponse(
        status="healthy",
        database="connected" if db_ok else "disconnected",
    )
