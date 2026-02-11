"""Chat routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import ChatRequest, ChatResponse
from services.chat_service import process_chat_message

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Process a chat message and return a response."""
    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )
    # Pass the full request through so process_chat_message can decide whether
    # to run the mocked financial QA flow or the general placeholder response.
    request.message = message
    return await process_chat_message(request=request, db=db)
