"""Conservative financial-document relevance classifier for uploaded chat attachments."""

import json
import os
from pathlib import Path
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.provider_factory import ProviderConfigurationError, build_chat_model


DEFAULT_MODEL = "gpt-4.1-mini"
POSITIVE_PHRASES = (
    "annual report",
    "quarterly report",
    "financial report",
    "financial statements",
    "investor presentation",
    "earnings presentation",
    "management discussion and analysis",
    "management discussion",
    "risk factors",
    "notes to accounts",
    "balance sheet",
    "income statement",
    "statement of profit and loss",
    "cash flow statement",
    "audited financials",
    "unaudited results",
    "revenue",
    "profit",
    "loss",
    "income",
    "ebitda",
    "debt",
    "equity",
    "shareholder",
    "business overview",
    "company overview",
    "operations",
    "segment reporting",
    "financial performance",
    "investor relations",
    "dividend",
)

NEGATIVE_PHRASES = (
    "recipe",
    "novel",
    "lecture notes",
    "course notes",
    "homework",
    "travel itinerary",
    "medical report",
    "cv ",
    "resume",
    "song lyrics",
    "code snippet",
    "programming tutorial",
    "installation guide",
    "user manual",
)


def _extract_json_object(text):
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _count_phrase_hits(text, phrases):
    lowered = (text or "").lower()
    return sum(1 for phrase in phrases if phrase in lowered)


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


def _looks_like_financial_document(text):
    positive = _count_phrase_hits(text, POSITIVE_PHRASES)
    negative = _count_phrase_hits(text, NEGATIVE_PHRASES)

    if positive >= 3:
        return True, positive, negative
    if positive >= 2 and negative == 0:
        return True, positive, negative
    if positive == 0 and negative >= 2:
        return False, positive, negative
    return None, positive, negative


def _heuristic_metadata(filename, text):
    stem = Path(filename).stem if filename else "document"
    document_type = Path(filename).suffix.lstrip(".").upper() if filename and "." in filename else "DOCUMENT"
    company = stem.replace("_", " ").replace("-", " ").strip() or "Unknown"

    relevant, positive_score, negative_score = _looks_like_financial_document(text)
    if relevant is True:
        reason = "Heuristic relevance check passed using report-style financial keywords."
    elif relevant is False:
        reason = "The document appears unrelated to company financial or investment research."
    else:
        reason = "Heuristic check is inconclusive."

    return {
        "relevant": relevant,
        "reason": reason,
        "document_type": document_type,
        "company": company,
        "positive_score": positive_score,
        "negative_score": negative_score,
    }


def classify_document_relevance(text, filename):
    text = (text or "").strip()
    if not text:
        return {
            "relevant": False,
            "reason": "The uploaded document did not contain extractable text.",
            "document_type": "DOCUMENT",
            "company": "Unknown",
        }

    heuristic = _heuristic_metadata(filename, text)
    if heuristic["relevant"] is True:
        heuristic["confidence"] = "high"
        return heuristic
    if heuristic["relevant"] is False:
        heuristic["confidence"] = "high"
        return heuristic

    api_key = os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", "")).strip()
    if not api_key:
        # Fall back to deterministic heuristics when the API is unavailable.
        heuristic["confidence"] = "medium"
        return heuristic

    model = os.environ.get("LLM_MODEL", os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)).strip() or DEFAULT_MODEL
    prompt_text = text[:8000]

    try:
        client = build_chat_model(default_model=model, temperature=0, max_tokens=250)
        response = client.invoke(
            [
                SystemMessage(
                    content=(
                        "You classify whether a document is relevant to company financial research. "
                        "Return only valid JSON with keys relevant, reason, document_type, company, and confidence. "
                        "Set relevant to true only if the document is about company financial information, corporate reporting, "
                        "investor material, financial performance, risks, or related investment-research content. "
                        "Be conservative: if unsure, set relevant to false."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Filename: {filename}\n\n"
                        f"Document excerpt:\n{prompt_text}\n\n"
                        "Return JSON now."
                    )
                ),
            ]
        )
        content = _message_text(getattr(response, "content", ""))
        parsed = _extract_json_object(content)
    except ProviderConfigurationError:
        parsed = None
    except Exception:
        parsed = None

    if not parsed:
        heuristic["confidence"] = "medium"
        return heuristic

    relevant = bool(parsed.get("relevant"))
    reason = (parsed.get("reason") or "").strip() or heuristic["reason"]
    document_type = (parsed.get("document_type") or heuristic["document_type"]).strip()
    company = (parsed.get("company") or heuristic["company"]).strip()
    confidence = (parsed.get("confidence") or "medium").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    return {
        "relevant": relevant,
        "reason": reason,
        "document_type": document_type,
        "company": company,
        "confidence": confidence,
    }
