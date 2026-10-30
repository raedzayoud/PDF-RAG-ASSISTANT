"""Split long PDF page text into smaller, overlapping passages."""

import re  # Regular expressions make it easy to normalize whitespace.

from app.models import DocumentChunk  # Reuse a shared structure for text and its source metadata.


class TextChunker:
    """Split text into chunks while retaining each chunk's PDF filename and page."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 150) -> None:
        # Validate the settings now rather than risk a loop that does not progress.
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be >= 0 and smaller than chunk_size")

        self.chunk_size = chunk_size  # Maximum number of characters in one chunk.
        self.overlap = overlap  # Number of characters shared with the following chunk.

    def split(self, text: str, source: str, page: int) -> list[DocumentChunk]:
        """Clean a page and return chunks that still know where they came from."""
        cleaned_text = re.sub(r"\s+", " ", text).strip()  # Collapse newlines and repeated spaces.
        if not cleaned_text:
            return []  # Ignore blank pages instead of creating empty embeddings.

        chunks: list[DocumentChunk] = []  # Store all the chunks produced from this page.
        start = 0  # Start at the first character in the cleaned text.

        while start < len(cleaned_text):  # Keep processing until all characters are covered.
            end = min(start + self.chunk_size, len(cleaned_text))  # Never read beyond the page text.
            chunk_text = cleaned_text[start:end]  # Take the current window of characters.
            chunks.append(DocumentChunk(text=chunk_text, source=source, page=page))  # Preserve citation data.

            if end == len(cleaned_text):
                break  # We have reached the end, so no more chunks are needed.

            start = end - self.overlap  # Repeat a few characters to avoid cutting context too sharply.

        return chunks  # Give the caller all passages from this page.
