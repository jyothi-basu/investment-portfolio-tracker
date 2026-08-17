"""Document loader that normalizes supported file types for the RAG ingestion pipeline."""

from pathlib import Path


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def _read_text_file(file_path):
    return file_path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf_file(file_path):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF support requires the pypdf package.") from exc

    reader = PdfReader(str(file_path))
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            # Keep PDF pages separate so downstream chunks can preserve page provenance.
            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                }
            )
    return pages


def _read_docx_file(file_path):
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("DOCX support requires the python-docx package.") from exc

    doc = Document(str(file_path))
    paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text and paragraph.text.strip()]
    return "\n".join(paragraphs)


def load_document_text(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document file not found: {path}")

    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported document type: {extension}")

    if extension in {".txt", ".md"}:
        return _read_text_file(path)
    if extension == ".pdf":
        return _read_pdf_file(path)
    if extension == ".docx":
        return _read_docx_file(path)

    raise ValueError(f"Unsupported document type: {extension}")
