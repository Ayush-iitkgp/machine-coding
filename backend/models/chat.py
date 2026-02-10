"""Chat-related database models."""
from sqlalchemy import Column, DateTime, Integer, Text, func

from database import Base


class ChatMessage(Base):
    """Chat message stored in the database."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
