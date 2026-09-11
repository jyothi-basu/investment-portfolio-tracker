"""Shared route helpers for template rendering, redirects, and form parsing."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.routing import NoMatchFound

from app.routes.auth import get_csrf_token, get_optional_user_id
from app.services import portfolio_service


FLASH_SESSION_KEY = "_fastapi_flash_messages"


# ---------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------
def parse_int(value):
    """Return an integer value or None when parsing fails."""

    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------
# Flash message helpers
# ---------------------------------------------------------------------
def flash_message(request: Request, message: str, category: str = "info") -> None:
    """Store a flash message in the session."""

    flashes = list(request.session.get(FLASH_SESSION_KEY, []))
    flashes.append({"category": category, "message": message})
    request.session[FLASH_SESSION_KEY] = flashes


def _pop_flash_messages(
    request: Request,
    with_categories: bool = False,
):
    """Retrieve and remove flashed messages from the session."""

    flashes = list(request.session.pop(FLASH_SESSION_KEY, []))

    if with_categories:
        return [(item["category"], item["message"]) for item in flashes]

    return [item["message"] for item in flashes]


# ---------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------
def render_template(
    request: Request,
    template_name: str,
    context: dict[str, Any] | None = None,
) -> HTMLResponse:
    """Render a Jinja template with the globals expected by the views."""

    user_id = get_optional_user_id(request)

    template_context: dict[str, Any] = {
        "request": request,
        "session": request.session,  # Allows {{ session.get(...) }} in templates
        "csrf_token": get_csrf_token(request),
        "url_for": lambda endpoint, **params: build_url_for(request, endpoint, **params),
        "get_flashed_messages": lambda with_categories=False: _pop_flash_messages(
            request,
            with_categories=with_categories,
        ),
        "logged_in_user": (
            portfolio_service.fetch_user(user_id) if user_id else None
        ),
    }

    if context:
        template_context.update(context)

    return request.app.state.templates.TemplateResponse(
        request=request,
        name=template_name,
        context=template_context,
    )


# ---------------------------------------------------------------------
# Redirect helper
# ---------------------------------------------------------------------
def build_url_for(request: Request, endpoint: str, **params):
    """Build a URL for named routes and fall back to query parameters.

    Starlette's `request.url_for()` only accepts path parameters. The chat page
    uses `chat_id` as a query parameter, so we preserve named-route generation
    for real path parameters and append query parameters when the route does not
    declare them.
    """

    try:
        return request.url_for(endpoint, **params)
    except NoMatchFound:
        base_url = request.url_for(endpoint)
        if not params:
            return base_url
        return base_url.include_query_params(**params)


def redirect_to(request: Request, endpoint: str, **params):
    return RedirectResponse(
        url=str(build_url_for(request, endpoint, **params)),
        status_code=303,
    )
