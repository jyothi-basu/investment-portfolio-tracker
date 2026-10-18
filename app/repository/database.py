"""SQLAlchemy engine and session configuration.

This module is the SQLAlchemy database infrastructure layer.
"""

from __future__ import annotations

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


load_dotenv()


def get_database_url() -> str:
    """Return the required database URL from the environment."""

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required. Configure it in .env for local development "
            "or in the deployment environment."
        )
    return database_url


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create a synchronous SQLAlchemy engine for the configured database."""

    url = database_url or get_database_url()
    return create_engine(url, future=True, pool_pre_ping=True)


engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the configured engine, creating it on first use."""

    if engine is None:
        configure_database(get_database_url())
    assert engine is not None
    return engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the configured session factory, creating it on first use."""

    if SessionLocal is None:
        configure_database(get_database_url())
    assert SessionLocal is not None
    return SessionLocal


def get_session() -> Generator[Session, None, None]:
    """Yield a repository session and always close it after use."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def configure_database(database_url: str) -> None:
    """Replace the configured engine and session factory."""

    global engine, SessionLocal
    if engine is not None:
        engine.dispose()
    engine = create_database_engine(database_url)
    SessionLocal = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
