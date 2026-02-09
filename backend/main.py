"""FastAPI application - Chat backend for Odin AI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Odin AI")

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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return a response."""
    message = request.message.strip()
    if not message:
        return ChatResponse(response="Please send a message.")
    # Echo-style response with a simple enhancement for demo
    return ChatResponse(
        response=f"You said: \"{message}\"\n\nOdin AI received your message. (This is a placeholder response—you can connect an LLM here.)"
    )
