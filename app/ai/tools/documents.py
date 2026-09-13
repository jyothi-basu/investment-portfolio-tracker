"""Trusted-context document search wrapper."""

from app.ai.context import get_trusted_chat_id, get_trusted_user_id
from app.ai.prompts import build_document_citation, format_document_chunks
from app.ai.rag.retriever import retrieve_relevant_chunks

from .common import json_content


def _dedupe_preserve_order(items):
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def search_uploaded_documents_for_context(query, user_id, chat_id, limit=8, retrieve_fn=None):
    query_text = (query or "").strip()
    if not query_text:
        return {"query": query_text, "results": [], "citations": []}

    safe_limit = max(1, min(int(limit or 8), 8))
    retrieve = retrieve_fn or retrieve_relevant_chunks
    chunks = retrieve(query_text, user_id, chat_id, limit=safe_limit)
    citations = _dedupe_preserve_order(
        [build_document_citation(chunk.get("metadata")) for chunk in chunks]
    )
    return {
        "query": query_text,
        "results": chunks,
        "citations": citations,
        "formatted_results": format_document_chunks(chunks) if chunks else "",
    }


from langchain_core.tools import tool


@tool("search_uploaded_documents")
def search_uploaded_documents(query: str, limit: int = 8) -> str:
    """Search the current chat's uploaded documents for relevant evidence."""

    result = search_uploaded_documents_for_context(
        query,
        get_trusted_user_id(),
        get_trusted_chat_id(),
        limit=limit,
    )
    return json_content(result)
