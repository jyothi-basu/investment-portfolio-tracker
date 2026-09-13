"""Application-help tool wrapper."""

from langchain_core.tools import tool

from app.ai.app_help import build_application_help


@tool("get_application_help")
def get_application_help(query: str = "") -> str:
    """Return application-usage guidance for the user's question."""

    return build_application_help(query=query)
