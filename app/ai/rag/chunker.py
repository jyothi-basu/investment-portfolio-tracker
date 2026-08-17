"""Structure-aware text chunking for uploaded investment documents."""

from pathlib import Path
import re


DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150
MARKDOWN_EXTENSIONS = {".md", ".markdown"}


def _normalize_text(text):
    lines = [line.rstrip() for line in (text or "").splitlines()]
    cleaned = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def _build_recursive_splitter(chunk_size, chunk_overlap):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be zero or greater")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:
        raise RuntimeError("Chunking requires the langchain-text-splitters package.") from exc

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
        is_separator_regex=False,
    )


def _split_markdown(text, chunk_size, chunk_overlap):
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter
    except ImportError as exc:
        raise RuntimeError("Markdown chunking requires the langchain-text-splitters package.") from exc

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ],
        strip_headers=False,
    )
    sections = header_splitter.split_text(text)
    recursive_splitter = _build_recursive_splitter(chunk_size, chunk_overlap)

    chunks = []
    for section in sections:
        section_text = _normalize_text(section.page_content)
        if not section_text:
            continue
        # Preserve section boundaries before falling back to recursive splitting.
        chunks.extend(recursive_splitter.split_text(section_text))
    return chunks


def _build_chunk_records(chunks, page_number=None, chunk_index_start=0):
    records = []
    for offset, chunk_text in enumerate(chunks):
        text = (chunk_text or "").strip()
        if not text:
            continue
        metadata = {"chunk_index": chunk_index_start + offset}
        if page_number is not None:
            metadata["page_number"] = page_number
        records.append({"text": text, "metadata": metadata})
    return records


def chunk_text(text, source_name=None, page_number=None, chunk_index_start=0, chunk_size=DEFAULT_CHUNK_SIZE, chunk_overlap=DEFAULT_CHUNK_OVERLAP):
    cleaned = _normalize_text(text)
    if not cleaned:
        return []

    suffix = Path(source_name).suffix.lower() if source_name else ""
    if suffix in MARKDOWN_EXTENSIONS:
        return _build_chunk_records(
            _split_markdown(cleaned, chunk_size, chunk_overlap),
            page_number=page_number,
            chunk_index_start=chunk_index_start,
        )

    recursive_splitter = _build_recursive_splitter(chunk_size, chunk_overlap)
    return _build_chunk_records(
        recursive_splitter.split_text(cleaned),
        page_number=page_number,
        chunk_index_start=chunk_index_start,
    )
