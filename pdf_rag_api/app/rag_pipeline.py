"""Coordinate the individual services that together implement RAG."""

from app.config import Settings  # Use one source of truth for application settings.
from app.embedding_service import EmbeddingService  # Convert PDF passages and questions to vectors.
from app.llm_service import LLMService  # Generate answers from the retrieved evidence.
from app.models import DocumentChunk  # Carry each passage's source metadata into the API response.
from app.pdf_loader import PDFLoader  # Read the source PDFs and split each page.
from app.retriever import Retriever  # Find relevant passages for a question.
from app.text_chunker import TextChunker  # Split the extracted text into overlapping pieces.
from app.vector_store import InMemoryVectorStore  # Keep the vector index in RAM for this learning version.


class RAGPipeline:
    """Expose a small interface so the API does not need to manage every RAG class."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings  # Preserve configuration for the document-sync behavior.
        chunker = TextChunker(settings.chunk_size, settings.chunk_overlap)  # Configure chunk size and overlap.
        self.pdf_loader = PDFLoader(settings.documents_dir, chunker)  # Connect the folder to the chunker.
        self.embedding_service = EmbeddingService(settings.embedding_model_name)  # Load the local encoder once.
        self.vector_store = InMemoryVectorStore()  # Create an initially empty vector index.
        self.retriever = Retriever(
            self.embedding_service, self.vector_store, top_k=settings.top_k
        )  # Reuse the same encoder to search the index.
        self.llm_service = LLMService(settings)  # Prepare the OpenAI client for response generation.
        self.indexed_chunk_count = 0  # Keep track of whether PDFs have been indexed.

    @property
    def is_ready(self) -> bool:
        """Tell API routes whether retrieval can run yet."""
        return self.vector_store.is_ready

    def sync_documents(self) -> int:
        """Load all PDFs and rebuild every embedding in the in-memory index."""
        chunks: list[DocumentChunk] = self.pdf_loader.load_chunks()  # Read PDFs and split page text.
        texts = [chunk.text for chunk in chunks]  # Extract only text for the embedding model.
        vectors = self.embedding_service.embed_documents(texts)  # Create a vector for each chunk.
        self.vector_store.replace_all(chunks, vectors)  # Replace chunks and vectors as one matched index.
        self.indexed_chunk_count = len(chunks)  # Record how many passages can be retrieved.
        return self.indexed_chunk_count

    def answer_question(
        self,
        question: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[tuple[DocumentChunk, float]]]:
        """Answer any question: document-grounded when the index exists, general otherwise."""
        if not question.strip():
            raise ValueError("Question cannot be empty.")

        results = self.retriever.retrieve(question) if self.is_ready else []
        answer = self.llm_service.answer(question, results, conversation_history)
        return answer, results  # Return both answer and sources so Angular can display citations.
