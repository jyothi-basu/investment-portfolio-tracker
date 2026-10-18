"""SQLAlchemy repository facade for application services."""

from __future__ import annotations

from app.repository import database
from app.repository.auth_repository import *
from app.repository.chat_repository import *
from app.repository.models import Base
from app.repository.portfolio_repository import *


def init_db() -> None:
    """Create the mapped tables for application startup and local setup."""

    Base.metadata.create_all(database.get_engine())
