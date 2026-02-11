"""Vector search over documents using Chroma with Ollama embeddings."""
from typing import List, Optional
import os

import chromadb
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
import httpx

from .chunks import FinancialChunk

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_data")


class OllamaEmbeddingFunction(EmbeddingFunction):
    """Chroma embedding function powered by an Ollama embedding model."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def __call__(self, input: Documents) -> Embeddings:  # type: ignore[override]
        texts: List[str]
        if isinstance(input, str):
            texts = [input]
        else:
            texts = list(input)

        if not texts:
            return []

        url = f"{self._base_url}/v1/embeddings"
        resp = httpx.post(
            url,
            json={"model": self._model, "input": texts},
            timeout=3000.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Ollama's /v1/embeddings returns {"data": [{"embedding": [...]}, ...], ...}
        if isinstance(data, dict) and "data" in data:
            return [item["embedding"] for item in data["data"]]

        raise RuntimeError(f"Unexpected Ollama embeddings response format: {data!r}")


# Persistent Chroma client - data is stored on disk at CHROMA_DB_PATH.
_client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH,
    settings=Settings(
        anonymized_telemetry=False,
    ),
)

_collection = _client.get_or_create_collection(
    name="financial_docs",
    embedding_function=OllamaEmbeddingFunction(OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL),
)

# Chunk IDs are assigned sequentially across the lifetime of the collection.
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

