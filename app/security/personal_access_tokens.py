"""Create and verify revocable personal access tokens for MCP clients."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.repository import db


TOKEN_PREFIX = "ipt_pat_"
_hasher = PasswordHasher()


class PersonalAccessTokenError(ValueError):
    """Raised when a PAT is malformed, expired, revoked, or unknown."""


@dataclass(frozen=True)
class IssuedPersonalAccessToken:
    token_id: int
    token: str
    name: str
    expires_at: str | None


def _parse_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PersonalAccessTokenError(
            "expires_at must be a valid ISO 8601 timestamp."
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def create_personal_access_token(
    user_id: int,
    name: str,
    expires_at: str | None = None,
) -> IssuedPersonalAccessToken:
    """Create a PAT and return its raw value exactly once."""

    normalized_name = (name or "").strip()
    if not normalized_name or len(normalized_name) > 100:
        raise PersonalAccessTokenError("name must contain between 1 and 100 characters.")

    expiry = _parse_expiry(expires_at)
    if expiry and expiry <= datetime.now(timezone.utc):
        raise PersonalAccessTokenError("expires_at must be in the future.")

    selector = secrets.token_hex(8)
    raw_token = f"{TOKEN_PREFIX}{selector}_{secrets.token_urlsafe(32)}"
    stored_expiry = expiry.isoformat() if expiry else None
    token_id = db.create_personal_access_token(
        user_id,
        selector,
        _hasher.hash(raw_token),
        normalized_name,
        stored_expiry,
    )
    return IssuedPersonalAccessToken(
        token_id=token_id,
        token=raw_token,
        name=normalized_name,
        expires_at=stored_expiry,
    )


def authenticate_personal_access_token(raw_token: str) -> int:
    """Verify a PAT and return its owner without exposing token details."""

    token = (raw_token or "").strip()
    if not token.startswith(TOKEN_PREFIX):
        raise PersonalAccessTokenError("Invalid personal access token.")

    remainder = token[len(TOKEN_PREFIX) :]
    selector, separator, secret = remainder.partition("_")
    if not separator or not selector or not secret:
        raise PersonalAccessTokenError("Invalid personal access token.")

    record = db.fetch_personal_access_token_by_selector(selector)
    if not record or record["revoked_at"]:
        raise PersonalAccessTokenError("Invalid personal access token.")

    expiry = _parse_expiry(record["expires_at"])
    if expiry and expiry <= datetime.now(timezone.utc):
        raise PersonalAccessTokenError("Personal access token has expired.")

    try:
        _hasher.verify(record["token_hash"], token)
    except (InvalidHashError, VerifyMismatchError) as exc:
        raise PersonalAccessTokenError("Invalid personal access token.") from exc

    db.touch_personal_access_token(record["token_id"])
    return int(record["user_id"])


def list_personal_access_tokens(user_id: int):
    tokens = []
    now = datetime.now(timezone.utc)
    for row in db.fetch_personal_access_tokens(user_id):
        token = dict(row)
        expiry = _parse_expiry(token["expires_at"])
        if token["revoked_at"]:
            token["status"] = "revoked"
        elif expiry and expiry <= now:
            token["status"] = "expired"
        else:
            token["status"] = "active"
        tokens.append(token)
    return tokens


def revoke_personal_access_token(token_id: int, user_id: int) -> bool:
    return bool(db.revoke_personal_access_token(token_id, user_id))
