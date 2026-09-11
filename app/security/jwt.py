"""Create and validate JWT access and refresh tokens for the application."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import os
import uuid

import jwt


class JWTConfigurationError(RuntimeError):
    """Raised when required JWT settings are missing or unsafe."""


class TokenValidationError(ValueError):
    """Raised when a token is malformed or fails claim validation."""


class TokenExpiredError(TokenValidationError):
    """Raised when a token has expired."""


@dataclass(frozen=True)
class JWTSettings:
    secret_key: str
    algorithm: str
    issuer: str
    audience: str
    access_minutes: int
    refresh_days: int
    cookie_secure: bool


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    refresh_jti: str
    access_expires_at: datetime
    refresh_expires_at: datetime


def _positive_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise JWTConfigurationError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise JWTConfigurationError(f"{name} must be a positive integer.")
    return value


@lru_cache(maxsize=1)
def get_jwt_settings() -> JWTSettings:
    """Load and validate JWT configuration from the environment."""

    secret_key = os.environ.get("JWT_SECRET_KEY", "").strip()
    if (
        len(secret_key) < 32
        or secret_key == "change-me-to-a-different-random-secret"
    ):
        raise JWTConfigurationError(
            "JWT_SECRET_KEY is required and must contain at least 32 random characters."
        )

    algorithm = os.environ.get("JWT_ALGORITHM", "HS256").strip().upper()
    if algorithm != "HS256":
        raise JWTConfigurationError(
            "JWT_ALGORITHM currently supports HS256 only. Set JWT_ALGORITHM=HS256."
        )

    issuer = os.environ.get(
        "JWT_ISSUER", "investment-portfolio-tracker"
    ).strip()
    audience = os.environ.get(
        "JWT_AUDIENCE", "investment-portfolio-api"
    ).strip()
    if not issuer or not audience:
        raise JWTConfigurationError(
            "JWT_ISSUER and JWT_AUDIENCE must not be empty."
        )

    return JWTSettings(
        secret_key=secret_key,
        algorithm=algorithm,
        issuer=issuer,
        audience=audience,
        access_minutes=_positive_int("JWT_ACCESS_TOKEN_MINUTES", 20),
        refresh_days=_positive_int("JWT_REFRESH_TOKEN_DAYS", 7),
        cookie_secure=os.environ.get("JWT_COOKIE_SECURE", "false").strip().lower()
        in {"1", "true", "yes", "on"},
    )


def _encode_token(user_id: int, token_type: str, expires_at: datetime, jti: str) -> str:
    settings = get_jwt_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
        "iss": settings.issuer,
        "aud": settings.audience,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_token_pair(user_id: int) -> TokenPair:
    """Create a short-lived access token and independently identified refresh token."""

    settings = get_jwt_settings()
    now = datetime.now(timezone.utc)
    access_expires_at = now + timedelta(minutes=settings.access_minutes)
    refresh_expires_at = now + timedelta(days=settings.refresh_days)
    access_jti = uuid.uuid4().hex
    refresh_jti = uuid.uuid4().hex
    return TokenPair(
        access_token=_encode_token(user_id, "access", access_expires_at, access_jti),
        refresh_token=_encode_token(
            user_id, "refresh", refresh_expires_at, refresh_jti
        ),
        refresh_jti=refresh_jti,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )


def decode_token(token: str, expected_type: str) -> dict:
    """Validate a JWT and require the expected access or refresh token type."""

    settings = get_jwt_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience=settings.audience,
            issuer=settings.issuer,
            options={"require": ["sub", "type", "jti", "iat", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("The authentication token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise TokenValidationError("The authentication token is invalid.") from exc

    if payload.get("type") != expected_type:
        raise TokenValidationError(
            f"Expected a {expected_type} token, but received another token type."
        )
    try:
        payload["user_id"] = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise TokenValidationError("The token subject is invalid.") from exc
    return payload
