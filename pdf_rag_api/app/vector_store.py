"""Keep chunk vectors in RAM and rank them by cosine similarity."""

import numpy as np  # Dot products and sorting are implemented efficiently by NumPy.

from app.models import DocumentChunk  # Each vector must stay aligned with its source text.


class InMemoryVectorStore:
    """Learning-friendly vector store; it is rebuilt after each backend restart."""

    def __init__(self) -> None:
        self.chunks: list[DocumentChunk] = []  # Source text and metadata, in vector order.
        self.vectors: np.ndarray | None = None  # One embedding row for each item in chunks.

    @property
    def is_ready(self) -> bool:
        """Report whether at least one chunk has been indexed."""
        return self.vectors is not None and bool(self.chunks)

    def replace_all(self, chunks: list[DocumentChunk], vectors: np.ndarray) -> None:
        """Replace the complete search index after a document sync."""
        if len(chunks) != len(vectors):  # Validate the essential text/vector alignment rule.
            raise ValueError("The number of chunks and vectors must match")
        self.chunks = list(chunks)  # Keep passages in exactly the same order as vector rows.
        self.vectors = vectors  # Save all vectors in memory for fast similarity search.

    def search(self, query_vector: np.ndarray, top_k: int = 4) -> list[tuple[DocumentChunk, float]]:
        """Return the top matching passages with their similarity scores."""
        if not self.is_ready:
            raise RuntimeError("The document index is empty. Run document synchronization first.")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        scores = self.vectors @ query_vector  # Inputs are normalized, so this is cosine similarity.
        best_indices = np.argsort(scores)[::-1][:top_k]  # Keep the highest scoring passages only.
        return [
            (self.chunks[int(index)], float(scores[index]))  # Pair each score with its source passage.
            for index in best_indices
        ]
