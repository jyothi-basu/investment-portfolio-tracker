"""Contract tests for the SQLAlchemy repository facade."""

from __future__ import annotations

import pytest

from app.repository import database
from app.repository import db
from tests.database_helpers import cleanup_test_database, configure_test_database


@pytest.fixture
def isolated_repository():
    original_engine = database.engine
    original_session_factory = database.SessionLocal
    configure_test_database()
    try:
        db.init_db()
        yield db
    finally:
        cleanup_test_database()
        database.engine = original_engine
        database.SessionLocal = original_session_factory


def test_user_and_account_inserts_return_integer_ids(isolated_repository):
    repository = isolated_repository

    user_id = repository.create_user("Contract User", "contract@example.com", "hash")
    account_id = repository.create_account(user_id, "Example Broker")

    assert isinstance(user_id, int)
    assert isinstance(account_id, int)
    assert repository.fetch_user_by_id(user_id)["email"] == "contract@example.com"
    assert repository.fetch_account(account_id, user_id)["broker_name"] == "Example Broker"


def test_account_queries_are_user_scoped(isolated_repository):
    repository = isolated_repository
    first_user = repository.create_user("First", "first@example.com", "hash")
    second_user = repository.create_user("Second", "second@example.com", "hash")
    account_id = repository.create_account(first_user, "Private Broker")

    assert repository.fetch_account(account_id, first_user) is not None
    assert repository.fetch_account(account_id, second_user) is None


def test_refresh_token_rotation_is_atomic(isolated_repository):
    repository = isolated_repository
    user_id = repository.create_user("Token User", "token@example.com", "hash")
    repository.create_refresh_token(user_id, "old-jti", "old-hash", "2099-01-01")

    assert repository.rotate_refresh_token(
        "old-jti", user_id, "new-jti", "new-hash", "2099-01-02"
    ) is True
    assert repository.fetch_active_refresh_token("old-jti", user_id) is None
    assert repository.fetch_active_refresh_token("new-jti", user_id)["token_hash"] == "new-hash"

    assert repository.rotate_refresh_token(
        "old-jti", user_id, "third-jti", "third-hash", "2099-01-03"
    ) is False
    assert repository.fetch_active_refresh_token("third-jti", user_id) is None
