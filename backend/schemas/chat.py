"""Chat API schemas."""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""

    response: str
