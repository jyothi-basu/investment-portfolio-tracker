"""JWT authentication, cookie handling, CSRF, and trusted AI request context."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hmac
import secrets

from fastapi import HTTPException, Request, status
from starlette.responses import Response

from app.ai.context import AssistantRequestContext, push_assistant_context
from app.repository import db
from app.security.jwt import (
    TokenExpiredError,
    TokenPair,
    TokenValidationError,
    decode_token,
    get_jwt_settings,
)
from app.services import auth_service


ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"
CSRF_SESSION_KEY = "csrf_token"


@dataclass(frozen=True)
class RequestAuthentication:
    user_id: int | None = None
    refreshed_tokens: TokenPair | None = None
    clear_cookies: bool = False


def _read_session_int(request: Request, key: str):
    value = request.session.get(key)
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if separator and scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return None


def authenticate_request(
    request: Request,
    *,
    allow_refresh: bool = True,
) -> RequestAuthentication:
    """Resolve trusted identity from a bearer token or HttpOnly JWT cookies."""

    bearer_token = _bearer_token(request)
    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE)

    if bearer_token:
        payload = decode_token(bearer_token, "access")
        if cookie_token:
            try:
                cookie_payload = decode_token(cookie_token, "access")
            except TokenValidationError:
                cookie_payload = None
            if cookie_payload and cookie_payload["user_id"] != payload["user_id"]:
                raise TokenValidationError(
                    "Bearer and cookie authentication identify different users."
                )
        return RequestAuthentication(user_id=payload["user_id"])

    if cookie_token:
        try:
            payload = decode_token(cookie_token, "access")
            return RequestAuthentication(user_id=payload["user_id"])
        except TokenExpiredError:
            if not allow_refresh:
                return RequestAuthentication()
        except TokenValidationError:
            return RequestAuthentication(clear_cookies=True)

    if not allow_refresh:
        return RequestAuthentication()

    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not refresh_token:
        return RequestAuthentication(clear_cookies=bool(cookie_token))

    try:
        pair = auth_service.rotate_refresh_token(refresh_token)
        payload = decode_token(pair.access_token, "access")
        return RequestAuthentication(
            user_id=payload["user_id"],
            refreshed_tokens=pair,
        )
    except TokenValidationError:
        return RequestAuthentication(clear_cookies=True)


def get_authenticated_user_id(request: Request) -> int:
    """Return the trusted user ID established by JWT middleware."""

    user_id = getattr(request.state, "authenticated_user_id", None)
    if user_id is None or not db.fetch_user_by_id(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return int(user_id)


def get_jwt_bearer_user_id(request: Request) -> int:
    """Require an explicit JWT access token rather than cookie authentication."""

    if not _bearer_token(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A JWT access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_authenticated_user_id(request)


def get_optional_user_id(request: Request) -> int | None:
    """Return an authenticated user ID when one is available."""

    user_id = getattr(request.state, "authenticated_user_id", None)
    if user_id is None or not db.fetch_user_by_id(user_id):
        return None
    return int(user_id)


def get_active_chat_id(request: Request):
    """Return the non-security UI preference for the last selected chat."""

    return _read_session_int(request, "active_chat_id")


def get_trusted_request_context(request: Request) -> AssistantRequestContext:
    """Return JWT identity and the current chat after ownership validation."""

    user_id = get_authenticated_user_id(request)
    chat_id = get_active_chat_id(request)
    if chat_id is None or not db.fetch_chat(chat_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid active chat is required for assistant requests.",
        )
    return AssistantRequestContext(user_id=user_id, chat_id=chat_id)


@contextmanager
def bind_trusted_request_context(request: Request):
    """Bind an ownership-verified user/chat context for assistant tools."""

    context = get_trusted_request_context(request)
    with push_assistant_context(user_id=context.user_id, chat_id=context.chat_id):
        yield context


def set_auth_cookies(response: Response, pair: TokenPair) -> None:
    """Store JWTs in browser-inaccessible cookies with bounded lifetimes."""

    settings = get_jwt_settings()
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        pair.access_token,
        max_age=settings.access_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        pair.refresh_token,
        max_age=settings.refresh_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Expire both authentication cookies."""

    settings = get_jwt_settings()
    for cookie_name in (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE):
        response.delete_cookie(
            cookie_name,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
        )


def get_csrf_token(request: Request) -> str:
    """Return a session-bound CSRF token for server-rendered forms."""

    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(request: Request, submitted_token) -> None:
    """Reject form submissions without the session CSRF token."""

    expected = request.session.get(CSRF_SESSION_KEY, "")
    supplied = str(submitted_token or "")
    if not expected or not hmac.compare_digest(expected, supplied):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The form security token is invalid or expired. Reload and try again.",
        )
