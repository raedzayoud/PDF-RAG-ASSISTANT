"""Small data objects used by the PDF retrieval part of the application."""

from dataclasses import dataclass  # Create a lightweight object without writing boilerplate methods.


@dataclass(frozen=True)
class DocumentChunk:
    """One passage from a PDF, with metadata needed to cite its origin."""

    text: str  # The text passage that can be included in the LLM context.
    source: str  # The source PDF's filename, for example accounting.pdf.
    page: int  # The one-based page number where this passage was found.
