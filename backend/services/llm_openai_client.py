"""OpenAI LLM client.

Provides a single `generate_answer` function used by the shared LLM router.
"""
from typing import Any, Dict
import os

import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com")
OPENAI_CHAT_URL = f"{OPENAI_API_BASE.rstrip('/')}/v1/chat/completions"


async def generate_answer(prompt: str) -> str:
    """Call the OpenAI Chat Completions API with the given prompt."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a financial analysis assistant. Answer the user's "
                    "question strictly based on the provided document excerpts."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(OPENAI_CHAT_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()

    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError):
        return "[LLM_ERROR] Unexpected response format from OpenAI API."

