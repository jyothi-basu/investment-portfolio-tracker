"""Phase 3 tests for SQLAlchemy repository sessions and compatibility output."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.repository import database
from app.repository.models import Base, User
from app.repository.serialization import model_to_dict, row_to_dict
from app.repository.session import session_scope


@pytest.fixture
def session_factory(tmp_path):
    engine = database.create_database_engine(f"sqlite:///{tmp_path / 'session.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def test_session_scope_commits_successful_work(session_factory):
    with session_scope(session_factory) as session:
        session.add(User(username="Committed", email="committed@example.com", password_hash="hash"))

    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == "committed@example.com"))
        assert user is not None


def test_session_scope_rolls_back_failed_work(session_factory):
    with pytest.raises(RuntimeError):
        with session_scope(session_factory) as session:
            session.add(User(username="Rolled Back", email="rollback@example.com", password_hash="hash"))
            raise RuntimeError("force rollback")

    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == "rollback@example.com"))
        assert user is None


def test_serializers_preserve_legacy_service_values():
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    row = {"amount": Decimal("12.3400"), "created_at": timestamp}

    assert row_to_dict(row) == {
        "amount": 12.34,
        "created_at": "2026-01-01T12:00:00+00:00",
    }


def test_model_to_dict_exposes_columns_without_relationships(session_factory):
    with session_scope(session_factory) as session:
        user = User(username="Serialized", email="serialized@example.com", password_hash="hash")
        session.add(user)
        session.flush()
        serialized = model_to_dict(user)

    assert serialized["username"] == "Serialized"
    assert serialized["email"] == "serialized@example.com"
    assert "chats" not in serialized
