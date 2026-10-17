"""SQLAlchemy repository for users, refresh tokens, and personal access tokens."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from app.repository.database import get_session_factory
from app.repository.models import PersonalAccessToken, RefreshToken, User, utc_now
from app.repository.serialization import model_to_dict
from app.repository.session import session_scope


def _as_utc_datetime(value: datetime | str) -> datetime:
    """Convert an ISO timestamp or datetime to an aware UTC datetime."""

    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        value = datetime.fromisoformat(normalized)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def fetch_user_by_id(user_id: int) -> dict[str, Any] | None:
    with session_scope() as session:
        user = session.get(User, user_id)
        if user is None:
            return None
        return {key: model_to_dict(user)[key] for key in ("user_id", "username", "email")}


def fetch_user_by_email(email: str) -> dict[str, Any] | None:
    with session_scope() as session:
        user = session.scalar(select(User).where(User.email == email))
        return model_to_dict(user) if user is not None else None


def email_exists(email: str) -> bool:
    with session_scope() as session:
        return session.scalar(select(User.user_id).where(User.email == email)) is not None


def create_user(username: str, email: str, password_hash: str) -> int:
    with session_scope() as session:
        user = User(username=username, email=email, password_hash=password_hash)
        session.add(user)
        session.flush()
        return user.user_id


def create_refresh_token(
    user_id: int,
    token_jti: str,
    token_hash: str,
    expires_at: datetime | str,
) -> int:
    with session_scope() as session:
        token = RefreshToken(
            user_id=user_id,
            token_jti=token_jti,
            token_hash=token_hash,
            expires_at=_as_utc_datetime(expires_at),
        )
        session.add(token)
        session.flush()
        return token.refresh_token_id


def fetch_active_refresh_token(token_jti: str, user_id: int) -> dict[str, Any] | None:
    with session_scope() as session:
        token = session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_jti == token_jti,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        return model_to_dict(token) if token is not None else None


def rotate_refresh_token(
    old_jti: str,
    user_id: int,
    new_jti: str,
    new_hash: str,
    new_expires_at: datetime | str,
) -> bool:
    """Revoke and replace a refresh token in one database transaction."""

    with session_scope() as session:
        token = session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_jti == old_jti,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        if token is None:
            return False

        token.revoked_at = utc_now()
        token.replaced_by_jti = new_jti
        session.add(
            RefreshToken(
                user_id=user_id,
                token_jti=new_jti,
                token_hash=new_hash,
                expires_at=_as_utc_datetime(new_expires_at),
            )
        )
        return True


def revoke_refresh_token(token_jti: str, user_id: int) -> int:
    with session_scope() as session:
        result = session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_jti == token_jti, RefreshToken.user_id == user_id)
            .values(revoked_at=utc_now())
        )
        return result.rowcount


def create_personal_access_token(
    user_id: int,
    selector: str,
    token_hash: str,
    name: str,
    expires_at: datetime | str | None,
) -> int:
    with session_scope() as session:
        token = PersonalAccessToken(
            user_id=user_id,
            token_selector=selector,
            token_hash=token_hash,
            name=name,
            expires_at=_as_utc_datetime(expires_at) if expires_at else None,
        )
        session.add(token)
        session.flush()
        return token.token_id


def fetch_personal_access_token_by_selector(selector: str) -> dict[str, Any] | None:
    with session_scope() as session:
        token = session.scalar(
            select(PersonalAccessToken).where(PersonalAccessToken.token_selector == selector)
        )
        return model_to_dict(token) if token is not None else None


def fetch_personal_access_tokens(user_id: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        tokens = session.scalars(
            select(PersonalAccessToken)
            .where(PersonalAccessToken.user_id == user_id)
            .order_by(PersonalAccessToken.created_at.desc(), PersonalAccessToken.token_id.desc())
        ).all()
        fields = ("token_id", "name", "created_at", "expires_at", "last_used_at", "revoked_at")
        return [{field: model_to_dict(token)[field] for field in fields} for token in tokens]


def touch_personal_access_token(token_id: int) -> int:
    with session_scope() as session:
        result = session.execute(
            update(PersonalAccessToken)
            .where(
                PersonalAccessToken.token_id == token_id,
                PersonalAccessToken.revoked_at.is_(None),
            )
            .values(last_used_at=utc_now())
        )
        return result.rowcount


def revoke_personal_access_token(token_id: int, user_id: int) -> int:
    with session_scope() as session:
        result = session.execute(
            update(PersonalAccessToken)
            .where(
                PersonalAccessToken.token_id == token_id,
                PersonalAccessToken.user_id == user_id,
                PersonalAccessToken.revoked_at.is_(None),
            )
            .values(revoked_at=utc_now())
        )
        return result.rowcount
