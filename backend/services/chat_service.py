"""Chat business logic."""
from sqlalchemy.ext.asyncio import AsyncSession

from models import ChatMessage
from schemas import ChatResponse

_PLACEHOLDER_RESPONSE = (
    "You said: \"{message}\"\n\n"
    "Odin AI received your message. (This is a placeholder response—you can connect an LLM here.)"
)


async def process_chat_message(
    message: str,
    db: AsyncSession,
) -> ChatResponse:
    """
    Process an incoming chat message and persist to database.

    Args:
        message: The user's message (non-empty, stripped).
        db: Database session.

    Returns:
        ChatResponse with the generated response text.
    """
    response_text = _PLACEHOLDER_RESPONSE.format(message=message)
    db.add(ChatMessage(message=message, response=response_text))
    return ChatResponse(response=response_text)
