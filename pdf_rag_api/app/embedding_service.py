"""Create local vector embeddings for PDF chunks and incoming questions."""

import numpy as np  # Use arrays for efficient similarity calculations.
from sentence_transformers import SentenceTransformer  # Load an embedding model that runs locally.


class EmbeddingService:
    """Convert text to normalized vectors using the same model for docs and questions."""

    def __init__(self, model_name: str) -> None:
        print(f"Loading local embedding model: {model_name}")  # Explain the first-run model download.
        self.model = SentenceTransformer(model_name)  # Initialize once and reuse for future requests.

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Encode many document passages into one matrix of normalized vectors."""
        return self.model.encode(
            texts,  # Every row in the output corresponds to one input passage.
            convert_to_numpy=True,  # Return NumPy data so we can perform vector math.
            normalize_embeddings=True,  # Unit vectors make dot product equal cosine similarity.
            show_progress_bar=True,  # Show progress when many passages are being indexed.
        )

    def embed_query(self, question: str) -> np.ndarray:
        """Encode a single user question with the same model and normalization."""
        vector_rows = self.model.encode(
            [question],  # The encoder expects a list even when there is one question.
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector_rows[0]  # Return the one-dimensional vector for the question.
