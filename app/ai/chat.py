"""LangChain-backed assistant runtime for tool-calling and final answer generation."""

from copy import deepcopy
import logging

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.ai.prompts import PROJECT_ASSISTANT_SYSTEM_PROMPT, format_citations
from app.ai.provider_factory import (
    ProviderConfigurationError,
    build_chat_model,
    get_chat_provider_settings,
)
from app.ai.tools import ToolExecutionResult, execute_tool_call, get_assistant_tools


load_dotenv()

logger = logging.getLogger(__name__)

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
    try:
        return build_chat_model(
            default_model=DEFAULT_MODEL,
            temperature=0.4,
            max_tokens=MAX_RESPONSE_TOKENS,
        )
    except ProviderConfigurationError as exc:
        raise ChatServiceError(str(exc)) from exc


def _log_provider_context():
    settings = get_chat_provider_settings(default_model=DEFAULT_MODEL)
    logger.info(
        "ai.chat.provider provider=%s model=%s max_tokens=%s",
        settings.provider,
        settings.model,
        MAX_RESPONSE_TOKENS,
    )
    return settings


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


def _message_debug_view(message):
    """Return a compact, log-safe view of a LangChain message."""

    additional_kwargs = getattr(message, "additional_kwargs", {}) or {}
    tool_calls = getattr(message, "tool_calls", None) or []
    return {
        "type": type(message).__name__,
        "content_preview": _message_text(getattr(message, "content", ""))[:200],
        "additional_kwargs_keys": sorted(additional_kwargs.keys()),
        "tool_call_count": len(tool_calls),
        "tool_call_ids": [
            getattr(tool_call, "id", None) if not isinstance(tool_call, dict) else tool_call.get("id")
            for tool_call in tool_calls
        ],
        "tool_call_names": [
            getattr(tool_call, "name", None) if not isinstance(tool_call, dict) else tool_call.get("name")
            for tool_call in tool_calls
        ],
        "tool_call_id": getattr(message, "tool_call_id", None),
    }


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
    assistant_tools = get_assistant_tools()
    logger.info("ai.chat.bind_tools tool_count=%s", len(assistant_tools))
    try:
        tool_bound_llm = llm.bind_tools(assistant_tools)
    except Exception:
        logger.exception("ai.chat.bind_tools failed")
        raise

    logger.info("ai.chat.bind_tools complete")
    citations = []

    for _ in range(MAX_TOOL_ROUNDS):
        logger.info("ai.chat.invoke start message_count=%s", len(messages))
        logger.info("ai.chat.invoke messages=%s", [_message_debug_view(message) for message in messages])
        try:
            response = tool_bound_llm.invoke(messages)
        except Exception:
            logger.exception("ai.chat.invoke failed")
            raise

        logger.info("ai.chat.invoke complete response_type=%s", type(response).__name__)
        response_kwargs = getattr(response, "additional_kwargs", {}) or {}
        logger.info("ai.chat.invoke response_message=%s", _message_debug_view(response))
        logger.info("ai.chat.invoke metadata keys=%s", sorted(response_kwargs.keys()))
        messages.append(deepcopy(response))

        tool_calls = [_normalise_tool_call(tool_call) for tool_call in _extract_tool_calls(response)]
        logger.info("ai.chat.tool_calls requested=%s", [tool_call["name"] for tool_call in tool_calls])
        if not tool_calls:
            answer = _message_text(response.content)
            if not answer:
                raise ChatServiceError("AI provider returned an empty response.")
            return _append_citations(answer, citations)

        for index, tool_call in enumerate(tool_calls, start=1):
            tool_name = tool_call["name"]
            tool_args = tool_call["args"] or {}
            tool_id = tool_call["id"] or f"{tool_name}-call-{index}"
            logger.info("ai.chat.tool_execute name=%s", tool_name)

            try:
                result = execute_tool_call(tool_name, tool_args)
            except Exception:
                logger.exception("ai.chat.tool_execute failed name=%s", tool_name)
                raise ChatServiceError(f"Tool execution failed for {tool_name}.") from None

            if isinstance(result, ToolExecutionResult):
                citations.extend(result.citations)
                tool_content = result.content
            else:
                tool_content = str(result)

            messages.append(ToolMessage(content=tool_content, tool_call_id=tool_id))

    raise ChatServiceError("The assistant could not complete the request after multiple tool calls.")


def get_chat_response(user_message, history=None, portfolio_context=None):
    """Generate a response with tool-calling and optional backward-compatible context."""

    provider_settings = None
    try:
        provider_settings = _log_provider_context()
        llm = _build_llm()
        messages = _build_messages(user_message, history=history)

        # The portfolio_context argument is kept only for backward compatibility.
        # The new architecture resolves portfolio/document/app-help context through tools.
        _ = portfolio_context

        return _run_tool_loop(llm, messages)
    except ProviderConfigurationError as exc:
        logger.exception("ai.chat.provider_configuration_failed")
        raise ChatServiceError(str(exc)) from exc
    except ChatServiceError:
        raise
    except Exception:
        if provider_settings is not None:
            logger.exception(
                "ai.chat.unhandled_failure provider=%s model=%s",
                provider_settings.provider,
                provider_settings.model,
            )
        else:
            logger.exception("ai.chat.unhandled_failure provider=unknown model=unknown")
        raise ChatServiceError("Unable to contact the AI provider right now.")
