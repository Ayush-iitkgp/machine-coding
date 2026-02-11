"""Shared chunk model used by vector search and LLM client."""
from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialChunk:
    """A chunk of a user-uploaded document."""

    id: int
    document_id: str
    section: str
    content: str

