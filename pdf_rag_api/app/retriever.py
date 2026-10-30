"""Turn a user's question into a vector and find relevant PDF passages."""

from app.embedding_service import EmbeddingService  # Encode the user question.
from app.models import DocumentChunk  # Type the retrieved passages and their source metadata.
from app.vector_store import InMemoryVectorStore  # Search the index of document vectors.


class Retriever:
    """Keep query embedding and vector search in one reusable component."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: InMemoryVectorStore,
        top_k: int = 4,
    ) -> None:
        self.embedding_service = embedding_service  # Same model used when indexing PDFs.
        self.vector_store = vector_store  # Search this vector index for relevant chunks.
        self.top_k = top_k  # Control how many passages are passed to the LLM.

    def retrieve(self, question: str) -> list[tuple[DocumentChunk, float]]:
        """Embed the question and return the best matching document chunks."""
        question_vector = self.embedding_service.embed_query(question)  # Represent the question numerically.
        return self.vector_store.search(question_vector, top_k=self.top_k)  # Rank passages by similarity.
