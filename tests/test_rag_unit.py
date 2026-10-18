"""RAG loader and chunking tests without Chroma or database access."""

from pathlib import Path
from unittest.mock import patch
import pytest

from app.ai.rag.chunker import chunk_text
from app.ai.rag.loader import load_document_text


class TestRAGUnit:
    def test_text_loader_reads_supported_text_file(self):
        path = Path("report.txt")
        with patch.object(Path, "exists", return_value=True), \
                patch.object(Path, "read_text", return_value="Revenue increased."):
            assert load_document_text(path) == "Revenue increased."

    def test_loader_rejects_unsupported_extension(self):
        path = Path("report.csv")
        with patch.object(Path, "exists", return_value=True):
            with pytest.raises(ValueError):
                load_document_text(path)

    def test_chunker_preserves_page_and_chunk_metadata(self):
        chunks = chunk_text(
            "# Revenue\n\nAster revenue was strong.",
            source_name="report.md",
            page_number=4,
            chunk_size=30,
            chunk_overlap=5,
        )
        assert chunks
        assert chunks[0]["metadata"]["page_number"] == 4
        assert chunks[0]["metadata"]["chunk_index"] == 0

    def test_chunker_rejects_invalid_overlap(self):
        with pytest.raises(ValueError):
            chunk_text("content", chunk_size=10, chunk_overlap=10)
