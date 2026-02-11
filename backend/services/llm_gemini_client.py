"""Gemini LLM client.

Provides a single `generate_answer` function used by the shared LLM router.
"""
import os

import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


async def generate_answer(prompt: str) -> str:
    """Call the Gemini Generative Language API with the given prompt."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    # Configure on demand so importing this module doesn't require the key.
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    return (getattr(response, "text", "") or "").strip()

