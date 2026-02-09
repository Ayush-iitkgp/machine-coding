"""FastAPI application - Chat backend for Odin AI."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import check_db_connection, get_db, init_db
from models import ChatMessage  # noqa: F401 - registers model with Base.metadata for init_db

_resp = (
    "You said: \"{message}\"\n\n"
    "Odin AI received your message. (This is a placeholder response—you can connect an LLM here.)"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield
    # Shutdown logic if needed


app = FastAPI(title="Odin AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.get("/health")
async def health():
    """Health check including database connectivity."""
    db_ok = await check_db_connection()
    return {"status": "healthy", "database": "connected" if db_ok else "disconnected"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Process a chat message and return a response."""
    message = request.message.strip()
    if not message:
        return ChatResponse(response="Please send a message.")
    response_text = _resp.format(message=message)
    db.add(ChatMessage(message=message, response=response_text))
    return ChatResponse(response=response_text)
