import json
import os

import requests
from dotenv import load_dotenv


load_dotenv()

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"
MAX_RESPONSE_TOKENS = 300


class ChatServiceError(RuntimeError):
    pass


def _build_messages(user_message, portfolio_context=None, history=None):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a project-specific assistant for the Investment Portfolio Tracker web app. "
                "Answer only questions that are directly related to this project, its codebase, its pages, "
                "its portfolio data, its transactions, its summaries, its setup, or its chat feature. "
                "If the user asks anything unrelated to this project, refuse briefly and say you can only help "
                "with this project. "
                "Do not claim access to live market data. "
                "Do not provide financial advice; keep answers informational."
            ),
        }
    ]

    if portfolio_context:
        messages.append(
            {
                "role": "system",
                "content": f"Current portfolio context:\n{portfolio_context}",
            }
        )

    for item in history or []:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message.strip()})
    return messages


def get_chat_response(user_message, portfolio_context=None, history=None):
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ChatServiceError("OPENROUTER_API_KEY is not set.")

    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip()
    if not model:
        model = DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    http_referer = os.environ.get("OPENROUTER_HTTP_REFERER", "").strip()
    app_title = os.environ.get("OPENROUTER_APP_TITLE", "Investment Portfolio Tracker").strip()
    if http_referer:
        headers["HTTP-Referer"] = http_referer
    if app_title:
        headers["X-OpenRouter-Title"] = app_title

    payload = {
        "model": model,
        "messages": _build_messages(user_message, portfolio_context=portfolio_context, history=history),
        "temperature": 0.4,
        "max_tokens": MAX_RESPONSE_TOKENS,
    }

    try:
        response = requests.post(
            OPENROUTER_CHAT_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise ChatServiceError("Unable to contact the AI provider right now.") from exc
    except ValueError as exc:
        raise ChatServiceError("AI provider returned an invalid response.") from exc

    try:
        content = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError, TypeError) as exc:
        raise ChatServiceError("AI provider returned an empty response.") from exc

    if not content:
        raise ChatServiceError("AI provider returned an empty response.")

    return content


if __name__ == "__main__":
    user_input = input("Ask any question about this site: ").strip()
    if not user_input:
        raise SystemExit("No question entered.")
    print(get_chat_response(user_input))
