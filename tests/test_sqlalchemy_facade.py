"""Tests for the SQLAlchemy database facade."""

from __future__ import annotations

import pytest

from app.repository import database
from app.repository import db
from tests.database_helpers import cleanup_test_database, configure_test_database


@pytest.fixture
def facade_database():
    original_engine = database.engine
    original_factory = database.SessionLocal
    configure_test_database()
    try:
        yield
    finally:
        cleanup_test_database()
        database.engine = original_engine
        database.SessionLocal = original_factory


def test_facade_creates_schema_and_delegates_domain_operations(facade_database):
    db.init_db()

    user_id = db.create_user("Facade User", "facade@example.com", "hash")
    account_id = db.create_account(user_id, "Broker")
    chat_id = db.create_chat(user_id)

    assert db.fetch_user_by_id(user_id)["email"] == "facade@example.com"
    assert db.fetch_account(account_id, user_id)["broker_name"] == "Broker"
    assert db.fetch_chat(chat_id, user_id)["user_id"] == user_id
