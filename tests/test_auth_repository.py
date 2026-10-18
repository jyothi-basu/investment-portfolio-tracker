"""Phase 4 tests for the isolated SQLAlchemy authentication repository."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from app.repository import database
from app.repository.auth_repository import (
    create_personal_access_token,
    create_refresh_token,
    create_user,
    email_exists,
    fetch_active_refresh_token,
    fetch_personal_access_token_by_selector,
    fetch_personal_access_tokens,
    fetch_user_by_email,
    fetch_user_by_id,
    revoke_personal_access_token,
    revoke_refresh_token,
    rotate_refresh_token,
    touch_personal_access_token,
)
from tests.database_helpers import cleanup_test_database, configure_test_database


@pytest.fixture
def auth_database():
    original_engine = database.engine
    original_factory = database.SessionLocal
    configure_test_database()
    try:
        yield
    finally:
        cleanup_test_database()
        database.engine = original_engine
        database.SessionLocal = original_factory


def test_user_repository_returns_dictionary_contract(auth_database):
    user_id = create_user("Auth User", "auth@example.com", "hash")

    assert email_exists("auth@example.com") is True
    assert fetch_user_by_id(user_id) == {
        "user_id": user_id,
        "username": "Auth User",
        "email": "auth@example.com",
    }
    assert fetch_user_by_email("auth@example.com")["password_hash"] == "hash"


def test_refresh_rotation_is_atomic_and_one_time_use(auth_database):
    user_id = create_user("Refresh User", "refresh@example.com", "hash")
    create_refresh_token(user_id, "old-jti", "old-hash", "2030-01-01T00:00:00+00:00")

    assert rotate_refresh_token(
        "old-jti", user_id, "new-jti", "new-hash", "2030-01-02T00:00:00+00:00"
    ) is True
    assert fetch_active_refresh_token("old-jti", user_id) is None
    assert fetch_active_refresh_token("new-jti", user_id)["token_hash"] == "new-hash"
    assert rotate_refresh_token(
        "old-jti", user_id, "third-jti", "third-hash", "2030-01-03T00:00:00+00:00"
    ) is False


def test_personal_access_token_repository_scopes_and_revokes_tokens(auth_database):
    user_id = create_user("PAT User", "pat@example.com", "hash")
    token_id = create_personal_access_token(
        user_id,
        "selector",
        "argon-hash",
        "Test client",
        datetime(2030, 1, 1, tzinfo=timezone.utc),
    )

    stored = fetch_personal_access_token_by_selector("selector")
    assert stored["token_hash"] == "argon-hash"
    assert fetch_personal_access_tokens(user_id)[0]["token_id"] == token_id
    assert touch_personal_access_token(token_id) == 1
    assert fetch_personal_access_token_by_selector("selector")["last_used_at"] is not None
    assert revoke_personal_access_token(token_id, user_id) == 1
    assert revoke_personal_access_token(token_id, user_id) == 0


def test_refresh_and_pat_expiry_values_are_serialized_as_utc_iso_strings(auth_database):
    user_id = create_user("UTC User", "utc@example.com", "hash")
    create_refresh_token(user_id, "utc-jti", "hash", "2030-01-01T00:00:00+05:30")
    create_personal_access_token(user_id, "utc-selector", "hash", "UTC", None)

    assert fetch_active_refresh_token("utc-jti", user_id)["expires_at"] == (
        "2029-12-31T18:30:00+00:00"
    )
    assert fetch_personal_access_token_by_selector("utc-selector")["expires_at"] is None
