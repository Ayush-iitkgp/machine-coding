"""LLM client router for answering questions using retrieved chunks.

Dispatches to provider-specific clients for Llama (Ollama), OpenAI, or Gemini.
By default, the Llama (Ollama) client is used; override with LLM_PROVIDER.
"""
from typing import Iterable, List, Tuple
import logging
import os

from .chunks import FinancialChunk
from . import llm_llama_client, llm_openai_client, llm_gemini_client

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "llama").lower()

logger = logging.getLogger(__name__)


async def _call_llm(prompt: str) -> str:
    """Call the configured LLM provider with a fully constructed prompt."""
    if LLM_PROVIDER == "openai":
        return await llm_openai_client.generate_answer(prompt)
    if LLM_PROVIDER == "gemini":
        return await llm_gemini_client.generate_answer(prompt)
    # Default to Llama/Ollama
    return await llm_llama_client.generate_answer(prompt)


async def answer_question_from_chunks(
    question: str,
    chunks: Iterable[FinancialChunk],
    max_chunks: int = 3,
) -> Tuple[str, List[FinancialChunk]]:
    """Build a prompt from the question and chunks and ask the configured LLM."""
    selected: List[FinancialChunk] = list(chunks)[:max_chunks]

    if not selected:
        fallback = (
            "I could not find any relevant information in the "
            "uploaded documents for your question:\n"
            f"\"{question}\""
        )
        return fallback, []

    context_lines: List[str] = []
    for idx, chunk in enumerate(selected, start=1):
        context_lines.append(
            f"{idx}. [doc={chunk.document_id} section={chunk.section}] {chunk.content}"
        )

    prompt = (
        "You are a financial analysis assistant. Answer the user's question "
        "strictly based on the provided document excerpts.\n\n"
        "Question:\n"
        f"{question}\n\n"
        "Document excerpts:\n"
        f"{chr(10).join(context_lines)}\n\n"
        "Answer in clear, concise language:"
    )

    try:
        answer = await _call_llm(prompt)
    except Exception as exc:  # noqa: BLE001
        # Log full details on the backend for debugging and monitoring.
        logger.exception(
            "LLM call failed for question %r with %d context chunks",
            question,
            len(selected),
        )
        # Return a generic, user-friendly message to the frontend.
        answer = "Unable to process the question at present. Please try again later."

    return (answer or "Unable to process the question at present. Please try again later."), selected

