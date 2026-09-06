"""FastAPI template and Flask compatibility helpers.

This module provides Flask-like helpers so existing Jinja templates can be reused
with minimal changes during the Flask → FastAPI migration.
"""

from __future__ import annotations
from typing import Any
from urllib.parse import urlencode
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.routing import NoMatchFound
from urllib.parse import urlencode
from app.services import portfolio_service


FLASH_SESSION_KEY = "_fastapi_flash_messages"


# ---------------------------------------------------------------------
# Flash message helpers (Flask compatible)
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
# Flask-compatible url_for()
# ---------------------------------------------------------------------
def flask_url_for(request: Request):
    """Flask-compatible url_for()."""

    def _url_for(endpoint: str, **params):
        if endpoint == "static" and "filename" in params:
            params["path"] = params.pop("filename")

        try:
            return str(request.url_for(endpoint, **params))
        except NoMatchFound:
            url = str(request.url_for(endpoint))

            if params:
                url = f"{url}?{urlencode(params)}"

            return url

    return _url_for


# ---------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------
def render_template(
    request: Request,
    template_name: str,
    context: dict[str, Any] | None = None,
) -> HTMLResponse:
    """Render a Jinja template with Flask-like globals."""

    user_id = request.session.get("user_id")

    template_context: dict[str, Any] = {
        "request": request,
        "session": request.session,  # Allows {{ session.get(...) }} in templates
        "url_for": flask_url_for(request),
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
# Redirect helper (Flask compatible)
# ---------------------------------------------------------------------
def redirect_to(request: Request, endpoint: str, **params):
    return RedirectResponse(
        url=flask_url_for(request)(endpoint, **params),
        status_code=303,
    )