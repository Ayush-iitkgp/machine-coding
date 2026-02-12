"""Chat API schemas."""
from typing import Literal, Optional

from pydantic import BaseModel


class HistoryMessage(BaseModel):
    """A single message in the conversation history."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str
    # Optional identifier for a specific financial document to query.
    document_id: Optional[str] = None
    # Mode hint so the backend can decide how to handle the message.
    # "financial_qa" will trigger the mocked vector search + LLM flow.
    mode: Optional[Literal["general", "financial_qa"]] = None
    # Conversation history for context (previous user and assistant messages).
    history: Optional[list[HistoryMessage]] = None


class FinancialChunkSummary(BaseModel):
    """Summary of a financial document chunk returned to the client."""

    id: int
    document_id: str
    document_name: Optional[str] = None
    section: str
    content: str


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""

    response: str
    # The document id that was used for retrieval (if any).
    document_id: Optional[str] = None
    # When a financial QA flow runs, this contains the specific chunks
    # that were used to construct the answer.
    retrieved_chunks: Optional[list[FinancialChunkSummary]] = None


class DocumentUploadResponse(BaseModel):
    """Response returned after uploading a document for QA."""

    document_id: str
    chunks: int
