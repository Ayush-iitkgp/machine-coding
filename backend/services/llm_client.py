"""LLM client for answering questions using retrieved chunks via Gemini.

This implementation calls the Gemini Generative Language API and returns both
the answer text and the concrete chunks that were used so callers can surface
them to the client.
"""
from typing import Iterable, List, Tuple
import os

import google.generativeai as genai

from .chunks import FinancialChunk

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not configured.")

genai.configure(api_key=GEMINI_API_KEY)


async def answer_question_from_chunks(
    question: str,
    chunks: Iterable[FinancialChunk],
    max_chunks: int = 3,
) -> Tuple[str, List[FinancialChunk]]:
    """Build a prompt from the question and chunks and ask the Gemini model.

    Args:
        question: The user's question.
        chunks: Iterable of FinancialChunk instances, typically from vector_search.
        max_chunks: Maximum number of chunks to include in the context.

    Returns:
        Tuple of:
            - answer: string returned by the LLM (or a fallback on failure).
            - used_chunks: the FinancialChunk objects included in the prompt.
    """
    selected: List[FinancialChunk] = list(chunks)[:max_chunks]

    if not selected:
        fallback = (
            "[LLM] I could not find any relevant information in the "
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
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        return text or "[LLM_ERROR] Empty response from Gemini.", selected
    except Exception as exc:  # noqa: BLE001
        answer = (
            "[LLM_ERROR] Failed to call the Gemini API. "
            f"Reason: {exc!r}\n\n"
            "Here are the raw excerpts so you can inspect them yourself:\n"
            f"{chr(10).join(context_lines)}"
        )
        return answer, selected

