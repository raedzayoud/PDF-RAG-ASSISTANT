"""Small offline tests for the chunking component; no LLM or PostgreSQL needed."""

import unittest  # Python's built-in test runner avoids another dependency.

from app.text_chunker import TextChunker  # Test the exact class used by the RAG pipeline.


class TextChunkerTests(unittest.TestCase):
    """Verify chunk overlap, metadata, blank input, and invalid settings."""

    def test_chunks_keep_source_and_page(self) -> None:
        chunker = TextChunker(chunk_size=8, overlap=2)
        chunks = chunker.split("abcdefghijklmnop", source="notes.pdf", page=3)
        self.assertEqual([chunk.text for chunk in chunks], ["abcdefgh", "ghijklmn", "mnop"])
        self.assertTrue(all(chunk.source == "notes.pdf" for chunk in chunks))
        self.assertTrue(all(chunk.page == 3 for chunk in chunks))

    def test_blank_text_returns_no_chunks(self) -> None:
        chunker = TextChunker()
        self.assertEqual(chunker.split("  \n\t ", source="empty.pdf", page=1), [])

    def test_invalid_overlap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            TextChunker(chunk_size=10, overlap=10)


if __name__ == "__main__":
    unittest.main()
