"""Convert SQLAlchemy values into the legacy repository contract."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect


def serialize_value(value: Any) -> Any:
    """Normalize ORM values for services that currently consume SQLite-style data."""

    if isinstance(value, datetime):
        timestamp = value
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy Row or RowMapping into a plain dictionary."""

    mapping = getattr(row, "_mapping", row)
    return {key: serialize_value(value) for key, value in mapping.items()}


def model_to_dict(model: Any) -> dict[str, Any]:
    """Serialize mapped columns without exposing ORM objects to services."""

    mapper = inspect(model).mapper
    return {
        attribute.key: serialize_value(getattr(model, attribute.key))
        for attribute in mapper.column_attrs
    }
