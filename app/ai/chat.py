"""LangChain-backed assistant runtime for tool-calling and final answer generation."""

import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.ai.prompts import PROJECT_ASSISTANT_SYSTEM_PROMPT, format_citations
from app.ai.tools import ToolExecutionResult, execute_tool_call, get_assistant_tools


load_dotenv()

DEFAULT_MODEL = "gpt-4.1-mini"
MAX_RESPONSE_TOKENS = 300
MAX_TOOL_ROUNDS = 4


class ChatServiceError(RuntimeError):
    """Raised when the assistant cannot complete a request safely."""


def _build_messages(user_message, history=None):
    messages = [
        SystemMessage(content=PROJECT_ASSISTANT_SYSTEM_PROMPT),
    ]

    for item in history or []:
        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message.strip()))
    return messages


def _build_llm():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ChatServiceError("OPENAI_API_KEY is not set.")

    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return ChatOpenAI(
        model=model,
        temperature=0.4,
        max_tokens=MAX_RESPONSE_TOKENS,
    )


def _message_text(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif "text" in item:
                    parts.append(item.get("text", ""))
        return "".join(parts).strip()
    if content is None:
        return ""
    return str(content).strip()


def _extract_tool_calls(message):
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        return tool_calls

    additional_kwargs = getattr(message, "additional_kwargs", {}) or {}
    raw_tool_calls = additional_kwargs.get("tool_calls") or []
    if raw_tool_calls:
        return raw_tool_calls

    return []


def _normalise_tool_call(tool_call):
    if isinstance(tool_call, dict):
        return {
            "name": tool_call.get("name"),
            "args": tool_call.get("args") or {},
            "id": tool_call.get("id"),
        }

    return {
        "name": getattr(tool_call, "name", None),
        "args": getattr(tool_call, "args", {}) or {},
        "id": getattr(tool_call, "id", None),
    }


def _append_citations(answer, citations):
    citations = [citation.strip() for citation in citations or [] if str(citation).strip()]
    deduped = []
    seen = set()
    for citation in citations:
        if citation not in seen:
            seen.add(citation)
            deduped.append(citation)

    if not deduped:
        return answer

    if "\n\nSources:\n" in answer:
        return answer

    citation_block = format_citations(deduped)
    if not citation_block:
        return answer

    return f"{answer.rstrip()}\n\n{citation_block}"


def _run_tool_loop(llm, messages):
    tool_bound_llm = llm.bind_tools(get_assistant_tools())
    citations = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = tool_bound_llm.invoke(messages)
        messages.append(response)

        tool_calls = [_normalise_tool_call(tool_call) for tool_call in _extract_tool_calls(response)]
        if not tool_calls:
            answer = _message_text(response.content)
            if not answer:
                raise ChatServiceError("AI provider returned an empty response.")
            return _append_citations(answer, citations)

        for index, tool_call in enumerate(tool_calls, start=1):
            tool_name = tool_call["name"]
            tool_args = tool_call["args"] or {}
            tool_id = tool_call["id"] or f"{tool_name}-call-{index}"

            try:
                result = execute_tool_call(tool_name, tool_args)
            except Exception as exc:
                raise ChatServiceError(f"Tool execution failed for {tool_name}.") from exc

            if isinstance(result, ToolExecutionResult):
                citations.extend(result.citations)
                tool_content = result.content
            else:
                tool_content = str(result)

            messages.append(ToolMessage(content=tool_content, tool_call_id=tool_id))

    raise ChatServiceError("The assistant could not complete the request after multiple tool calls.")


def get_chat_response(user_message, history=None, portfolio_context=None):
    """Generate a response with tool-calling and optional backward-compatible context."""

    llm = _build_llm()
    messages = _build_messages(user_message, history=history)

    # The portfolio_context argument is kept only for backward compatibility.
    # The new architecture resolves portfolio/document/app-help context through tools.
    _ = portfolio_context

    try:
        return _run_tool_loop(llm, messages)
    except ChatServiceError:
        raise
    except Exception as exc:
        raise ChatServiceError("Unable to contact the AI provider right now.") from exc
