"""Document upload and indexing routes."""
from uuid import uuid4
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette import status

from schemas import DocumentUploadResponse
from services import vector_search
from pypdf import PdfReader


router = APIRouter(prefix="/documents", tags=["documents"])


def _extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF byte stream using pypdf."""
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read PDF file: {exc!r}",
        ) from exc

    texts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            texts.append(page_text)

    combined = "\n".join(texts).strip()
    if not combined:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded PDF contains no extractable text.",
        )
    return combined


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
    chunks = await vector_search.add_document(document_id=document_id, content=text)

    if chunks <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks were created from the uploaded document.",
        )

    return DocumentUploadResponse(document_id=document_id, chunks=chunks)

