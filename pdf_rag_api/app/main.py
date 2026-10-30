"""FastAPI entry point: expose PDF RAG and chat memory as REST endpoints."""

from contextlib import asynccontextmanager  # Run setup and cleanup around the API's lifetime.
from pathlib import Path  # Safely extract the uploaded filename from a path.
from typing import Annotated  # Combine FastAPI dependency and form metadata with types.
import uuid  # Create and validate conversation identifiers.

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile  # API tools.
from fastapi.middleware.cors import CORSMiddleware  # Allow Angular running on another local port.
from sqlalchemy.orm import Session  # Type the injected database session.

from app.api_schemas import (  # Explicit JSON shapes that Angular can rely on.
    ChatRequest,
    ChatResponse,
    MessageResponse,
    SessionResponse,
    SessionSummary,
    SourceReference,
    UploadResponse,
)
from app.chat_memory import ChatMemoryStore  # Read and persist messages in PostgreSQL.
from app.config import Settings  # Load model, path, and CORS settings.
from app.database import create_tables, get_db  # Initialize tables and inject per-request DB sessions.
from app.rag_pipeline import RAGPipeline  # Combine PDF retrieval and LLM answer generation.

# Keep the maximum upload size low for this local learning project.
MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MiB maximum per PDF upload.
settings = Settings()  # Read configuration once when the API module is imported.
memory_store = ChatMemoryStore()  # Stateless helper; the actual messages live in PostgreSQL.


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare database tables and the RAG services before the first request."""
    create_tables()  # Create chat tables if this is the first run.
    rag_pipeline = RAGPipeline(settings)  # Load embeddings and the OpenAI client once, not per request.
    app.state.rag_pipeline = rag_pipeline  # Share the initialized pipeline with API routes.

    # Sync PDFs that are already in documents/. The API can still start if none are present.
    try:
        chunk_count = rag_pipeline.sync_documents()
        print(f"Startup indexing complete: {chunk_count} PDF chunks.")
    except RuntimeError as exc:
        print(f"PDF index not ready yet: {exc}")

    yield  # FastAPI now accepts requests; resources stay available during this period.
    # There are no manually managed RAG resources to close in this starter project.


app = FastAPI(
    title="PDF RAG API",  # Title shown by the interactive Swagger UI.
    description="Ask questions about PDFs with GPT-OSS, plus PostgreSQL conversation memory.",
    version="1.0.0",
    lifespan=lifespan,
)

# Angular's development server normally runs on port 4200; browsers require CORS permission.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),  # Allow only configured frontend origins.
    allow_credentials=True,
    allow_methods=["*"],  # Allow GET, POST, OPTIONS, and other standard REST methods.
    allow_headers=["*"],  # Allow JSON and future authorization headers from Angular.
)


def get_pipeline(request: Request) -> RAGPipeline:
    """Retrieve the one initialized RAG pipeline from FastAPI application state."""
    return request.app.state.rag_pipeline


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Basic status endpoint useful for checking that FastAPI is running."""
    return {"status": "ok"}


@app.post("/api/sessions", response_model=SessionResponse, status_code=201)
def create_chat_session(db: Annotated[Session, Depends(get_db)]) -> SessionResponse:
    """Create a new chat thread and return its ID to store in Angular."""
    session_row = memory_store.create_session(db)  # Save an empty conversation in PostgreSQL.
    return SessionResponse(session_id=session_row.id, created_at=session_row.created_at)


@app.get("/api/sessions", response_model=list[SessionSummary])
def list_chat_sessions(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),  # Keep the sidebar list bounded.
) -> list[SessionSummary]:
    """Return recent conversations so Angular can render sidebar history."""
    return [SessionSummary(**row) for row in memory_store.list_sessions(db, limit=limit)]


@app.get("/api/sessions/{session_id}/messages", response_model=list[MessageResponse])
def read_chat_history(
    session_id: uuid.UUID,  # FastAPI validates the URL parameter as a UUID.
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),  # Avoid returning unbounded message history.
) -> list[MessageResponse]:
    """Return stored messages so Angular can restore a prior conversation."""
    if memory_store.find_session(db, session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session was not found.")
    rows = memory_store.get_messages(db, session_id, limit=limit)
    return [
        MessageResponse(
            id=row.id, role=row.role, content=row.content, created_at=row.created_at
        )
        for row in rows
    ]


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,  # FastAPI validates JSON into this Python object.
    db: Annotated[Session, Depends(get_db)],  # One short-lived DB session for this API request.
    pipeline: Annotated[RAGPipeline, Depends(get_pipeline)],  # Reuse the initialized RAG components.
) -> ChatResponse:
    """Answer a question, use recent chat memory, and persist the completed turn."""
    question = body.question.strip()  # Remove spaces so a whitespace-only question is rejected.
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    if memory_store.find_session(db, body.session_id) is None:
        raise HTTPException(status_code=404, detail="Create a chat session before asking questions.")

    # Load previous turns before saving the current question, so we do not duplicate it in the prompt.
    history = memory_store.get_recent_history(
        db, body.session_id, limit=settings.history_messages
    )

    try:
        answer, matches = pipeline.answer_question(question, conversation_history=history)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # Log the technical error on the backend but don't expose internals or secrets to the browser.
        print(f"RAG request failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Could not generate an answer. Check Groq API availability, model ID, and rate limits.",
        ) from exc

    memory_store.save_turn(db, body.session_id, question, answer)  # Persist both sides of the turn.
    sources = [
        SourceReference(
            filename=chunk.source,
            page=chunk.page,
            similarity=score,
            snippet=chunk.text[:300],  # Keep the response manageable while showing its evidence.
        )
        for chunk, score in matches
    ]
    return ChatResponse(session_id=body.session_id, answer=answer, sources=sources)


@app.post("/api/documents/upload", response_model=UploadResponse, status_code=201)
def upload_pdf(
    file: Annotated[UploadFile, File(description="PDF file with selectable text")],
    pipeline: Annotated[RAGPipeline, Depends(get_pipeline)],
) -> UploadResponse:
    """Save one PDF supplied by Angular; call /api/documents/sync afterwards."""
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Upload a file whose extension is .pdf.")

    safe_filename = Path(file.filename.replace("\\", "/")).name  # Drop client-supplied directory components.
    try:
        content = file.file.read(MAX_PDF_BYTES + 1)  # Read at most the configured limit plus one byte.
    finally:
        file.file.close()  # Close the upload stream even if reading fails.

    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds the 20 MiB upload limit.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file does not look like a PDF.")

    destination = settings.documents_dir / safe_filename  # Save inside the configured document folder.
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)  # Store the original PDF; it is indexed by the sync endpoint.
    return UploadResponse(
        filename=safe_filename,
        message="PDF uploaded. Call POST /api/documents/sync to update the search index.",
    )


@app.post("/api/documents/sync")
def sync_documents(
    pipeline: Annotated[RAGPipeline, Depends(get_pipeline)],
) -> dict[str, int | str]:
    """Re-read all PDFs and rebuild the complete in-memory vector index."""
    try:
        chunk_count = pipeline.sync_documents()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "indexed", "chunks": chunk_count}


@app.get("/api/documents/status")
def document_status(
    pipeline: Annotated[RAGPipeline, Depends(get_pipeline)],
) -> dict[str, int | bool]:
    """Report whether PDFs have been indexed in this API process."""
    return {
        "ready": pipeline.is_ready,
        "indexed_chunks": pipeline.indexed_chunk_count,
    }
