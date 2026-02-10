"""Health check API schemas."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response body for health endpoint."""

    status: str
    database: str
