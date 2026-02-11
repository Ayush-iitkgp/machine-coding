"""Chat business logic."""
from sqlalchemy.ext.asyncio import AsyncSession

from models import ChatMessage
from schemas import ChatRequest, ChatResponse, FinancialChunkSummary
from services.llm_client import answer_question_from_chunks
from services.vector_search import search_similar_chunks

_PLACEHOLDER_RESPONSE = (
    "You said: \"{message}\"\n\n"
    "Odin AI received your message. (This is a placeholder response—you can connect an LLM here.)"
)


def _is_financial_question(request: ChatRequest) -> bool:
    """Determine whether the incoming message should use financial QA.

    Priority:
    - If `mode` is explicitly set to \"financial_qa\", always treat as such.
    - Otherwise, fall back to a simple keyword-based heuristic.
    """
    return True
    if request.mode == "financial_qa":
        return True

    text = request.message.lower()
    financial_keywords = [
        "income statement",
        "balance sheet",
        "cash flow",
        "net income",
        "revenue",
        "expenses",
        "financial statement",
        "annual report",
    ]
    return any(keyword in text for keyword in financial_keywords)


async def _handle_financial_question(
    request: ChatRequest,
    db: AsyncSession,
) -> ChatResponse:
    """Process a financial-document question using mocked retrieval + LLM."""
    chunks = await search_similar_chunks(
        query=request.message,
        document_id=request.document_id,
        limit=5,
    )
    response_text, used_chunks = await answer_question_from_chunks(
        question=request.message,
        chunks=chunks,
        max_chunks=3,
    )
    db.add(ChatMessage(message=request.message, response=response_text))
    retrieved = [
            FinancialChunkSummary(
                id=chunk.id,
                document_id=chunk.document_id,
                section=chunk.section,
                content=chunk.content,
            )
            for chunk in used_chunks
        ]

    return ChatResponse(
        response=response_text,
        document_id=request.document_id,
        retrieved_chunks=retrieved or None,
    )


async def process_chat_message(
    request: ChatRequest,
    db: AsyncSession,
) -> ChatResponse:
    """
    Process an incoming chat message and persist to database.

    For general chat, this returns a simple placeholder echo response.
    For financial-document questions, it runs a mocked vector search over an
    in-memory financial corpus and constructs a deterministic answer via a
    mocked LLM client.

    Args:
        request: ChatRequest containing the user's message and optional context.
        db: Database session.

    Returns:
        ChatResponse with the generated response text.
    """
    if _is_financial_question(request):
        return await _handle_financial_question(request=request, db=db)

    response_text = _PLACEHOLDER_RESPONSE.format(message=request.message)
    # db.add(ChatMessage(message=request.message, response=response_text))
    return ChatResponse(response=response_text)
