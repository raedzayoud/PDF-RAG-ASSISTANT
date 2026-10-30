"""SQLAlchemy table definitions for persistent chat sessions and messages."""

import uuid  # Generate globally unique IDs for chat sessions.
from datetime import datetime, timezone  # Store timestamps in UTC.

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid  # SQL column types.
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column  # SQLAlchemy 2.0 ORM building blocks.


class Base(DeclarativeBase):
    """Base class from which SQLAlchemy discovers all database tables."""


class ChatSessionRow(Base):
    """One conversation thread; a user can open multiple separate sessions."""

    __tablename__ = "chat_sessions"  # Actual table name created in PostgreSQL.

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )  # Unique conversation identifier sent to Angular.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )  # Save the time the conversation was created.


class ChatMessageRow(Base):
    """One user or assistant message belonging to a chat session."""

    __tablename__ = "chat_messages"  # Persistent history is stored in this table.

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )  # Connect each message to its conversation.
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # Usually 'user' or 'assistant'.
    content: Mapped[str] = mapped_column(Text, nullable=False)  # The complete message text.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )  # Save when the message was added.
