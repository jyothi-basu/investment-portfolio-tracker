"""Authentication service for issuing, rotating, and revoking JWT refresh tokens."""

from __future__ import annotations

from datetime import timezone
import hashlib
import hmac

from app.repository import db
from app.security.jwt import TokenPair, TokenValidationError, create_token_pair, decode_token


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token_pair(user_id: int) -> TokenPair:
    """Issue tokens and persist only a hash of the refresh token."""

    pair = create_token_pair(user_id)
    db.create_refresh_token(
        user_id=user_id,
        token_jti=pair.refresh_jti,
        token_hash=_token_hash(pair.refresh_token),
        expires_at=pair.refresh_expires_at.astimezone(timezone.utc).isoformat(),
    )
    return pair


def rotate_refresh_token(refresh_token: str) -> TokenPair:
    """Validate and atomically replace a one-time-use refresh token."""

    payload = decode_token(refresh_token, "refresh")
    user_id = payload["user_id"]
    token_jti = payload["jti"]
    stored = db.fetch_active_refresh_token(token_jti, user_id)
    if not stored or not hmac.compare_digest(
        stored["token_hash"], _token_hash(refresh_token)
    ):
        raise TokenValidationError("The refresh token is revoked or unknown.")

    pair = create_token_pair(user_id)
    rotated = db.rotate_refresh_token(
        old_jti=token_jti,
        user_id=user_id,
        new_jti=pair.refresh_jti,
        new_hash=_token_hash(pair.refresh_token),
        new_expires_at=pair.refresh_expires_at.astimezone(timezone.utc).isoformat(),
    )
    if not rotated:
        raise TokenValidationError("The refresh token has already been used.")
    return pair


def revoke_refresh_token(refresh_token: str) -> None:
    """Revoke the supplied refresh token when it is valid and known."""

    try:
        payload = decode_token(refresh_token, "refresh")
    except TokenValidationError:
        return
    db.revoke_refresh_token(payload["jti"], payload["user_id"])
