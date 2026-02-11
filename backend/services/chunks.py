"""Shared chunk model used by vector search and LLM client."""
from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialChunk:
    """A chunk of a user-uploaded document."""

    id: int
    document_id: str
    document_name: str | None
    section: str
    content: str

