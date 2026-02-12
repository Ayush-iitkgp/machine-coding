"""Document upload and indexing routes."""
from io import BytesIO
from uuid import uuid4

import pdfplumber
from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette import status

from schemas import DocumentUploadResponse
from services import vector_search

router = APIRouter(prefix="/documents", tags=["documents"])


def _ensure_utf8(text: str) -> str:
    """Normalize text to valid UTF-8, replacing unencodable characters."""
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _table_to_text(table: list[list]) -> str:
    """Format a table (list of rows) as readable text with pipe separators."""
    if not table:
        return ""
    lines: list[str] = []
    for row in table:
        cells = [str(c).strip() if c is not None else "" for c in row]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def _extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF byte stream using pdfplumber.

    Uses pdfplumber's table detection to preserve table structure; falls back
    to plain text extraction for non-table content.
    """
    try:
        pdf = pdfplumber.open(BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read PDF file: {exc!r}",
        ) from exc

    sections: list[str] = []
    with pdf:
        for i, page in enumerate(pdf.pages):
            page_sections: list[str] = []

            # Extract tables first (preserves row/column structure)
            tables = page.extract_tables()
            if tables:
                for j, table in enumerate(tables):
                    table_text = _table_to_text(table)
                    if table_text.strip():
                        page_sections.append(f"[Table {j + 1}]\n{table_text}")

            # Extract remaining text (non-table content)
            page_text = page.extract_text()
            if page_text and page_text.strip():
                page_sections.append(page_text.strip())

            if page_sections:
                sections.append("\n\n".join(page_sections))

    combined = "\n\n".join(sections).strip()
    if not combined:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded PDF contains no extractable text.",
        )
    return _ensure_utf8(combined)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Upload a PDF document, extract text, and index it for QA."""
    if file.content_type not in {"application/pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    text = _extract_text_from_pdf(raw_bytes)

    document_id = str(uuid4())
    chunks = await vector_search.add_document(
        document_id=document_id,
        content=text,
        document_name=file.filename,
        max_chars_per_chunk=vector_search.CHUNK_MAX_CHARS,
        overlap_chars=vector_search.CHUNK_OVERLAP_CHARS,
    )

    if chunks <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks were created from the uploaded document.",
        )

    return DocumentUploadResponse(document_id=document_id, chunks=chunks)

