"""Central configuration loaded from environment variables and the local .env file."""

import os  # Read settings that were supplied by the shell or a .env file.
from dataclasses import dataclass  # Keep related configuration values in one small object.
from pathlib import Path  # Build paths in a way that works on Windows, macOS, and Linux.

from dotenv import load_dotenv  # Load local development secrets from .env.

# Use the project root as the base for folders and the .env file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")  # Existing shell variables take precedence over .env values.


@dataclass(frozen=True)
class Settings:
    """Settings shared by the RAG components, API, and database connection."""

    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b")
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    documents_dir: Path = PROJECT_ROOT / os.getenv("DOCUMENTS_DIR", "documents")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    top_k: int = int(os.getenv("TOP_K", "4"))
    # This URL is used by Python running on your computer, so the host is localhost.
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://rag_user:rag_password_change_me@localhost:5432/rag_memory",
    )
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200"
        ).split(",")
        if origin.strip()
    )
    history_messages: int = int(os.getenv("HISTORY_MESSAGES", "10"))
