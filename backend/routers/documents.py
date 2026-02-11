"""Document upload routes for vector-based QA."""
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pypdf import PdfReader

from schemas import DocumentUploadResponse
from services.vector_search import add_document

router = APIRouter(tags=["documents"])


def _extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF file."""
    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            parts.append(page_text)
    return "\n\n".join(parts)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Upload a PDF document to be used for question answering."""
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    if not (file.filename and file.filename.lower().endswith(".pdf")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    try:
        text = _extract_text_from_pdf(raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read PDF: {exc!r}",
        ) from exc

    text = text.strip()
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF has no readable text.",
        )

    document_id = str(uuid4())
    chunks = await add_document(document_id=document_id, content=text)
    if chunks == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded document is empty after preprocessing.",
        )

    return DocumentUploadResponse(document_id=document_id, chunks=chunks)


