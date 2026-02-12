"""Document upload and indexing routes."""
import logging
import re
from io import BytesIO
from uuid import uuid4

import pdfplumber
from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette import status

from schemas import DocumentUploadResponse
from services import vector_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


def _ensure_utf8(text: str) -> str:
    """Normalize text to valid UTF-8, replacing unencodable characters."""
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _replace_cid_codes(text: str) -> str:
    """Replace (cid:XX) codes with Unicode characters."""
    def _repl(match: re.Match[str]) -> str:
        try:
            cid = int(match.group(1))
            if 0 <= cid <= 0x10FFFF:
                char = chr(cid)
                return char if char.isprintable() or char in "\n\t" else " "
        except (ValueError, OverflowError):
            pass
        return ""
    return re.sub(r"\(cid:(\d+)\)", _repl, text)


def _readability_score(text: str) -> float:
    """Score 0-1: higher = more likely readable (common letters, numbers, punctuation)."""
    if not text or not text.strip():
        return 0.0
    clean = text.replace("\n", " ").replace("\t", " ")
    if not clean:
        return 0.0
    good = sum(1 for c in clean if c.isalnum() or c in " .,$%()-/")
    return good / len(clean)


def _looks_garbled(text: str) -> bool:
    """True if text likely has font encoding issues (e.g. CID/Identity-H).

    Financial PDFs typically contain words like revenue, income, million, billion.
    Garbled text won't have these.
    """
    if not text or len(text) < 100:
        return False
    lower = text.lower()
    financial_words = [
        "revenue", "income", "million", "billion", "total", "year",
        "consolidated", "operating", "expenses", "net", "financial",
    ]
    return not any(w in lower for w in financial_words)


def _table_to_text(table: list[list]) -> str:
    """Format a table (list of rows) as readable text with pipe separators."""
    if not table:
        return ""
    lines: list[str] = []
    for row in table:
        cells = [
            _replace_cid_codes(str(c).strip() if c is not None else "")
            for c in row
        ]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def _extract_with_pymupdf(data: bytes) -> str | None:
    """Extract text using PyMuPDF (MuPDF). Often handles CID/font issues better than pdfminer."""
    try:
        import fitz
    except ImportError:
        return None

    try:
        doc = fitz.open(stream=BytesIO(data), filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        logger.warning("PyMuPDF failed to open PDF: %s", exc)
        return None

    sections: list[str] = []
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text("text")
            if page_text and page_text.strip():
                sections.append(page_text.strip())
    finally:
        doc.close()

    combined = "\n\n".join(sections).strip()
    return combined if combined else None


def _extract_with_pymupdf_ocr(data: bytes) -> str | None:
    """Extract text using PyMuPDF OCR (requires Tesseract). Use when normal extraction is garbled."""
    try:
        import fitz
    except ImportError:
        return None

    try:
        doc = fitz.open(stream=BytesIO(data), filetype="pdf")
    except Exception:  # noqa: BLE001
        return None

    sections: list[str] = []
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                tp = page.get_textpage_ocr()
                page_text = page.get_text(textpage=tp)
                if page_text and page_text.strip():
                    sections.append(page_text.strip())
            except Exception as exc:  # noqa: BLE001
                logger.warning("OCR failed for page %d: %s", page_num, exc)
    finally:
        doc.close()

    combined = "\n\n".join(sections).strip()
    return combined if combined else None


def _extract_with_pdfplumber(data: bytes) -> str:
    """Extract text using pdfplumber (uses pdfminer). Preserves table structure."""
    pdf = pdfplumber.open(BytesIO(data))
    sections: list[str] = []
    with pdf:
        for i, page in enumerate(pdf.pages):
            page_sections: list[str] = []

            tables = page.extract_tables()
            if tables:
                for j, table in enumerate(tables):
                    table_text = _table_to_text(table)
                    if table_text.strip():
                        page_sections.append(f"[Table {j + 1}]\n{table_text}")

            page_text = page.extract_text()
            if page_text and page_text.strip():
                page_sections.append(_replace_cid_codes(page_text.strip()))

            if page_sections:
                sections.append("\n\n".join(page_sections))

    return "\n\n".join(sections).strip()


def _extract_text_from_pdf(data: bytes) -> str:
    """Extract text from PDF. Tries PyMuPDF first (better font handling), then pdfplumber, then OCR.

    PyMuPDF (MuPDF) often handles CID/Identity-H fonts better than pdfminer (used by pdfplumber).
    When both work, prefer PyMuPDF. If readability is very low, try OCR (requires Tesseract).
    """
    # 1. Try PyMuPDF first (often better for CID/font encoding issues)
    pymupdf_text = _extract_with_pymupdf(data)
    if pymupdf_text:
        score = _readability_score(pymupdf_text)
        garbled = _looks_garbled(pymupdf_text)
        logger.info("PyMuPDF: %d chars, readability %.2f, garbled=%s", len(pymupdf_text), score, garbled)
        if score >= 0.35 and not garbled:
            return _ensure_utf8(pymupdf_text)
        best_text, best_score, best_garbled = pymupdf_text, score, garbled
    else:
        best_text, best_score, best_garbled = None, 0.0, True

    # 2. Try pdfplumber (good table structure)
    try:
        pdfplumber_text = _extract_with_pdfplumber(data)
        if pdfplumber_text:
            score = _readability_score(pdfplumber_text)
            garbled = _looks_garbled(pdfplumber_text)
            logger.info("pdfplumber: %d chars, readability %.2f, garbled=%s", len(pdfplumber_text), score, garbled)
            if score > best_score or best_text is None:
                best_text, best_score, best_garbled = pdfplumber_text, score, garbled
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfplumber failed: %s", exc)

    if best_text:
        if best_garbled or best_score < 0.35:
            logger.info("Text appears garbled (score %.2f), trying OCR", best_score)
            ocr_text = _extract_with_pymupdf_ocr(data)
            if ocr_text:
                ocr_score = _readability_score(ocr_text)
                ocr_garbled = _looks_garbled(ocr_text)
                if not ocr_garbled or ocr_score > best_score:
                    logger.info("OCR: %d chars, readability %.2f", len(ocr_text), ocr_score)
                    return _ensure_utf8(ocr_text)
        return _ensure_utf8(best_text)

    # 3. OCR as last resort
    ocr_text = _extract_with_pymupdf_ocr(data)
    if ocr_text:
        return _ensure_utf8(ocr_text)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Uploaded PDF contains no extractable text.",
    )


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


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str) -> None:
    """Delete a document's chunks from the vector store. Use before re-uploading to fix garbled extraction."""
    removed = vector_search.delete_document(document_id)
    if removed == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No document found with id {document_id}",
        )

