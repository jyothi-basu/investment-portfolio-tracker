"""Shared SQLAlchemy database setup for repository and integration tests."""

from __future__ import annotations

import os

from app.repository import database
from app.repository.models import Base


def get_test_database_url() -> str:
    """Return the dedicated SQLAlchemy URL used by the test suite."""

    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "TEST_DATABASE_URL is required for tests. Use a separate database, "
            "not the application database."
        )
    return url


def configure_test_database() -> None:
    """Point the repository at a clean database for one test scope."""

    database.configure_database(get_test_database_url())
    Base.metadata.drop_all(database.get_engine())
    Base.metadata.create_all(database.get_engine())


def cleanup_test_database() -> None:
    """Remove tables created by a test scope and release the engine."""

    if database.engine is not None:
        Base.metadata.drop_all(database.get_engine())
        database.get_engine().dispose()
