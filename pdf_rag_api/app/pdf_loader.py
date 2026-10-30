"""Read PDFs from the documents folder and turn their pages into text chunks."""

from pathlib import Path  # Handle PDF folders and filenames portably.

from pypdf import PdfReader  # Extract selectable text from each PDF page.

from app.models import DocumentChunk  # Standard structure passed into the embedding stage.
from app.text_chunker import TextChunker  # Component responsible for splitting page text.


class PDFLoader:
    """Load every PDF in one folder, preserving source filenames and page numbers."""

    def __init__(self, documents_dir: Path, chunker: TextChunker) -> None:
        self.documents_dir = documents_dir  # Store the folder to scan.
        self.chunker = chunker  # Reuse the configured text chunker for every page.

    def load_chunks(self) -> list[DocumentChunk]:
        """Extract text from all PDFs and return all non-empty chunks."""
        self.documents_dir.mkdir(parents=True, exist_ok=True)  # Create the folder on first use.
        pdf_files = sorted(self.documents_dir.glob("*.pdf"))  # Only load PDFs directly in this folder.

        if not pdf_files:
            raise RuntimeError(
                f"No PDF files found in '{self.documents_dir}'. Add PDFs and call /api/documents/sync."
            )

        all_chunks: list[DocumentChunk] = []  # Gather passages from all files into one searchable collection.
        failures: list[str] = []  # Report problematic PDFs while still allowing other files to load.

        for pdf_path in pdf_files:  # Process files in a predictable alphabetical order.
            try:
                reader = PdfReader(str(pdf_path))  # Open the PDF using pypdf.
                for page_number, page in enumerate(reader.pages, start=1):  # Citation pages start at 1.
                    page_text = page.extract_text() or ""  # Scanned images may have no selectable text.
                    all_chunks.extend(
                        self.chunker.split(page_text, source=pdf_path.name, page=page_number)
                    )  # Split this page and add its passages to the overall list.
            except Exception as exc:  # Catch a broken PDF without hiding the problem from the user.
                failures.append(f"{pdf_path.name}: {exc}")

        if not all_chunks:
            details = " | ".join(failures)
            raise RuntimeError(
                "No selectable PDF text could be extracted. Scanned PDFs need OCR. " + details
            )

        if failures:
            print("Some PDFs could not be loaded: " + " | ".join(failures))

        return all_chunks  # Return the source-aware chunks to the embedding stage.
