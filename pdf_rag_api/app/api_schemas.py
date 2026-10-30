"""Pydantic request/response schemas that define the API contract for Angular."""

import uuid  # Keep API session IDs type-safe.
from datetime import datetime  # Describe the time each message was saved.
from typing import Literal  # Restrict roles to supported values.

from pydantic import BaseModel, Field  # Validate JSON request bodies and serialize responses.


class SessionResponse(BaseModel):
    """Response returned after creating a conversation session."""

    session_id: uuid.UUID
    created_at: datetime


class SessionSummary(BaseModel):
    """One row in the frontend conversation-history list."""

    session_id: uuid.UUID
    created_at: datetime
    message_count: int
    title: str | None


class ChatRequest(BaseModel):
    """JSON body Angular sends when the user asks a question."""

    session_id: uuid.UUID = Field(description="ID returned by POST /api/sessions")
    question: str = Field(min_length=1, max_length=4000, description="Question about the PDFs")


class SourceReference(BaseModel):
    """One PDF passage used to prepare the answer."""

    filename: str
    page: int
    similarity: float
    snippet: str


class ChatResponse(BaseModel):
    """Answer and source information returned to the Angular chat component."""

    session_id: uuid.UUID
    answer: str
    sources: list[SourceReference]


class MessageResponse(BaseModel):
    """A saved message for rendering previous conversation history."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class UploadResponse(BaseModel):
    """Result of a PDF upload request."""

    filename: str
    message: str
