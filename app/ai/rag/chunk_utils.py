"""Shared chunk and metadata preparation for vector-store backends."""


def build_metadata(
    document_id,
    user_id,
    chat_id,
    original_filename,
    chunk_index,
    document_type=None,
    company=None,
    page_number=None,
):
    metadata = {
        "document_id": int(document_id),
        "user_id": int(user_id),
        "chat_id": int(chat_id),
        "original_filename": original_filename,
        "chunk_index": int(chunk_index),
    }
    if page_number is not None:
        metadata["page_number"] = int(page_number)
    if document_type:
        metadata["document_type"] = document_type
    if company:
        metadata["company"] = company
    return metadata


def prepare_chunks(
    document_id,
    user_id,
    chat_id,
    original_filename,
    chunks,
    document_type=None,
    company=None,
):
    if not chunks:
        raise ValueError("chunks must not be empty")

    prepared = []
    for default_index, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            text = (chunk.get("text") or "").strip()
            source_metadata = dict(chunk.get("metadata") or {})
            chunk_index = source_metadata.get("chunk_index", default_index)
            page_number = source_metadata.get("page_number")
        else:
            text = (chunk or "").strip()
            chunk_index = default_index
            page_number = None

        if not text:
            continue

        prepared.append(
            {
                "id": f"document-{document_id}-chunk-{int(chunk_index)}",
                "text": text,
                "metadata": build_metadata(
                    document_id=document_id,
                    user_id=user_id,
                    chat_id=chat_id,
                    original_filename=original_filename,
                    chunk_index=chunk_index,
                    document_type=document_type,
                    company=company,
                    page_number=page_number,
                ),
            }
        )

    if not prepared:
        raise ValueError("chunks must not be empty")
    return prepared
