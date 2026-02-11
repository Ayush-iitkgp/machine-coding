"""Vector search over financial documents using Chroma with Gemini embeddings.

This uses a real in-memory Chroma collection and Gemini embedding function
to perform semantic similarity search over the financial corpus.
"""
from typing import List, Optional
import os

import chromadb
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
import google.generativeai as genai

from .chunks import FinancialChunk

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Use a model that supports embedContent in the current v1beta API.
GEMINI_EMBED_MODEL = os.getenv("gemini-embedding-001", "gemini-embedding-001")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not configured.")

genai.configure(api_key=GEMINI_API_KEY)


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Chroma embedding function powered by Gemini."""

    def __init__(self, model: str):
        self._model = model

    def __call__(self, input: Documents) -> Embeddings:  # type: ignore[override]
        # Chroma passes a list of strings as `input`.
        texts: List[str]
        if isinstance(input, str):
            texts = [input]
        else:
            texts = list(input)

        embeddings: Embeddings = []
        for text in texts:
            res = genai.embed_content(model=self._model, content=text)
            embeddings.append(res["embedding"])
        return embeddings


# In-memory Chroma client (no persistence on disk).
_client = chromadb.Client(
    Settings(
        anonymized_telemetry=False,
    )
)

_collection = _client.create_collection(
    name="financial_docs",
    embedding_function=GeminiEmbeddingFunction(GEMINI_EMBED_MODEL),
)

# Start with an empty collection; only user-uploaded documents are indexed.
_next_chunk_id = 1


async def add_document(
    document_id: str,
    content: str,
    max_chars_per_chunk: int = 800,
) -> int:
    """Add a new document to the vector store by chunking and embedding it.

    Args:
        document_id: Logical identifier for the uploaded document.
        content: Raw text content of the document.
        max_chars_per_chunk: Maximum characters per chunk before splitting.

    Returns:
        Number of chunks added.
    """
    text = content.strip()
    if not text:
        return 0

    # Simple chunking: split on double newlines, then hard-wrap long paragraphs.
    chunks: list[str] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        while len(block) > max_chars_per_chunk:
            chunk, block = block[:max_chars_per_chunk], block[max_chars_per_chunk:]
            chunks.append(chunk.strip())
        if block:
            chunks.append(block)

    if not chunks:
        return 0

    global _next_chunk_id

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for idx, chunk_text in enumerate(chunks, start=1):
        chunk_id = _next_chunk_id
        _next_chunk_id += 1

        ids.append(str(chunk_id))
        documents.append(chunk_text)
        metadatas.append(
            {
                "document_id": document_id,
                "section": f"uploaded_chunk_{idx}",
                "chunk_id": chunk_id,
            }
        )

    _collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


async def search_similar_chunks(
    query: str,
    document_id: Optional[str] = None,
    limit: int = 5,
) -> List[FinancialChunk]:
    """Return the top-N chunks that best match the query using Chroma + Gemini."""
    where = {"document_id": document_id} if document_id is not None else None

    results = _collection.query(
        query_texts=[query],
        n_results=limit,
        where=where,
    )

    metadatas = results.get("metadatas", [[]])[0]
    documents = results.get("documents", [[]])[0]

    chunks: List[FinancialChunk] = []
    for meta, content in zip(metadatas, documents):
        chunks.append(
            FinancialChunk(
                id=int(meta.get("chunk_id")),
                document_id=str(meta.get("document_id")),
                section=str(meta.get("section")),
                content=str(content),
            )
        )

    return chunks

