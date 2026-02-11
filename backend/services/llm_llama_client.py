"""Llama (Ollama) LLM client.

Uses an Ollama-hosted Llama model via the OpenAI-compatible chat completions API.
"""
from typing import Any, Dict
import os

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


async def generate_answer(prompt: str) -> str:
    """Call the Ollama (Llama) chat API with the given prompt."""
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/v1/chat/completions"

    payload: Dict[str, Any] = {
        "model": OLLAMA_MODEL,
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
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()

    # Ollama's OpenAI-compatible endpoint mirrors the Chat Completions shape.
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError):
        return "[LLM_ERROR] Unexpected response format from Ollama chat API."

