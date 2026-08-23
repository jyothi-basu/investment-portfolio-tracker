"""STDIO MCP server that exposes the existing document RAG pipeline."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from app.ai.prompts import format_document_chunks
from app.ai.rag.retriever import retrieve_relevant_chunks


load_dotenv()


def _require_env_int(name: str) -> int:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set.")

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc


def create_server() -> FastMCP:
    """Create the MCP server with the configured trusted user and chat scope."""

    user_id = _require_env_int("MCP_USER_ID")
    chat_id = _require_env_int("MCP_CHAT_ID")

    mcp = FastMCP("Investment Portfolio Tracker RAG")

    @mcp.tool()
    def search_uploaded_documents(query: str) -> str:
        """Search uploaded documents for evidence in the configured user/chat scope."""

        query_text = (query or "").strip()
        if not query_text:
            return "No document query was provided."

        chunks = retrieve_relevant_chunks(query_text, user_id, chat_id, limit=8)
        if not chunks:
            return f"No relevant uploaded document evidence was found for the query: {query_text!r}."

        return "\n".join(
            [
                f"Document search results for: {query_text}",
                format_document_chunks(chunks),
            ]
        )

    return mcp
