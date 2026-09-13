"""Common result and serialization helpers for shared tools."""

from dataclasses import dataclass, field
import json
import sqlite3


@dataclass(frozen=True)
class ToolExecutionResult:
    """Structured internal output used by the assistant executor."""

    content: str
    citations: list[str] = field(default_factory=list)


def normalize_for_json(value):
    """Convert SQLite rows and nested containers to JSON-safe values."""

    if isinstance(value, sqlite3.Row):
        return {
            key: normalize_for_json(value[key])
            for key in value.keys()
        }
    if isinstance(value, dict):
        return {
            key: normalize_for_json(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [normalize_for_json(item) for item in value]
    return value


def json_content(value) -> str:
    """Serialize structured service data for a model tool message."""

    return json.dumps(normalize_for_json(value), ensure_ascii=False, default=str)
