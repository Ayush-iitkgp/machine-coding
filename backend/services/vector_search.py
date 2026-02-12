"""Vector search over documents using Chroma with Ollama embeddings."""
import logging
import os
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
import httpx

from .chunks import FinancialChunk

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Default: store under backend/chroma_data so path is independent of process cwd.
_DEFAULT_CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_data")
CHROMA_DB_PATH = os.path.abspath(os.getenv("CHROMA_DB_PATH", _DEFAULT_CHROMA_PATH))

CHUNK_MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "800"))
CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "100"))

# Minimum similarity (0-1) to include a chunk. Uses cosine: similarity = 1 - distance.
# Only chunks with similarity >= this threshold are returned.
SIMILARITY_THRESHOLD = float(os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.2"))


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
    document_name: str | None = None,
    max_chars_per_chunk: int = 800,
    overlap_chars: int = 100,
) -> int:
    """Add a new document to the vector store by chunking and embedding it.

    Args:
        document_id: Logical identifier for the uploaded document.
        content: Raw text content of the document.
        document_name: Optional display name for the document.
        max_chars_per_chunk: Maximum characters per chunk before splitting.
        overlap_chars: Number of characters to overlap between consecutive chunks.
            Overlap helps preserve context at chunk boundaries (e.g. split sentences).

    Returns:
        Number of chunks added.
    """
    text = content.strip()
    if not text:
        return 0

    overlap_chars = min(max(0, overlap_chars), max_chars_per_chunk // 2)
    step = max_chars_per_chunk - overlap_chars

    def _split_with_overlap(block: str) -> list[str]:
        """Split a block into overlapping chunks."""
        if len(block) <= max_chars_per_chunk:
            return [block] if block else []
        result: list[str] = []
        start = 0
        while start < len(block):
            chunk = block[start : start + max_chars_per_chunk]
            if chunk.strip():
                result.append(chunk.strip())
            start += step
        return result

    chunks: list[str] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        for chunk_text in _split_with_overlap(block):
            if chunk_text:
                chunks.append(chunk_text)

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
                "document_name": document_name,
                "section": f"uploaded_chunk_{idx}",
                "chunk_id": chunk_id,
            }
        )

    _collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def delete_document(document_id: str) -> int:
    """Delete all chunks for a document. Returns number of chunks removed."""
    try:
        result = _collection.get(
            where={"document_id": document_id},
            include=["metadatas"],
        )
        ids = result.get("ids", [])
        if ids:
            _collection.delete(ids=ids)
            logger.info("Deleted %d chunks for document_id=%s", len(ids), document_id)
        return len(ids)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to delete document %s: %s", document_id, exc)
        return 0


async def search_similar_chunks(
    query: str,
    document_id: Optional[str] = None,
    limit: int = 5,
) -> List[FinancialChunk]:
    """Return the top-N chunks that best match the query. Only returns chunks with similarity >= 70%."""
    where = {"document_id": document_id} if document_id is not None else None

    # Query more candidates to filter by threshold, then trim to limit
    results = _collection.query(
        query_texts=[query],
        n_results=min(limit * 4, 50),  # fetch extra for threshold filtering
        where=where,
        include=["metadatas", "documents", "distances"],
    )

    metadatas = results.get("metadatas", [[]])[0]
    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    # If Chroma didn't return distances (e.g. older version), include all results
    use_threshold = len(distances) == len(metadatas)

    chunks: List[FinancialChunk] = []
    for i, (meta, content) in enumerate(zip(metadatas, documents)):
        if use_threshold:
            distance = float(distances[i])
            # Cosine: similarity = 1 - distance (distance in [0, 2]).
            # L2 (Chroma default): for normalized vectors, cos_sim ≈ 1 - d²/2.
            if distance <= 1.0:
                similarity = 1.0 - distance  # cosine or small L2
            else:
                similarity = max(0.0, 1.0 - distance * distance / 2.0)  # L2 normalized
            if similarity < SIMILARITY_THRESHOLD:
                logger.debug(
                    "Excluded chunk id=%s similarity=%.2f (threshold=%.2f)",
                    meta.get("chunk_id"),
                    similarity,
                    SIMILARITY_THRESHOLD,
                )
                continue

        chunks.append(
            FinancialChunk(
                id=int(meta.get("chunk_id")),
                document_id=str(meta.get("document_id")),
                document_name=str(meta.get("document_name")) if meta.get("document_name") is not None else None,
                section=str(meta.get("section")),
                content=str(content),
            )
        )
        if len(chunks) >= limit:
            break

    chunks = chunks[:limit]

    logger.info(
        "Vector search completed: query=%r, document_id=%s, limit=%d, num_results=%d",
        query,
        document_id,
        limit,
        len(chunks),
    )
    for i, chunk in enumerate(chunks, start=1):
        preview = chunk.content[:300] + "..." if len(chunk.content) > 300 else chunk.content
        logger.info(
            "Matching chunk[%d] id=%s doc=%s section=%s content=%s",
            i,
            chunk.id,
            chunk.document_id,
            chunk.section,
            preview,
        )

    return chunks

