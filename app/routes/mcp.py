"""Expose PAT management, conversation discovery, and authenticated MCP SSE."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.mcp.sse import handle_sse_message, open_sse_connection
from app.mcp.streamable_http import handle_streamable_http
from app.routes.auth import (
    get_authenticated_user_id,
    get_jwt_bearer_user_id,
    validate_csrf_token,
)
from app.routes.common import flash_message, redirect_to, render_template
from app.security.personal_access_tokens import (
    PersonalAccessTokenError,
    authenticate_personal_access_token,
    create_personal_access_token,
    list_personal_access_tokens,
    revoke_personal_access_token,
)
from app.services import chat_service


logger = logging.getLogger(__name__)
router = APIRouter()


class PersonalAccessTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    expires_at: str | None = None


def _render_pat_page(request: Request, user_id: int, raw_token: str | None = None):
    response = render_template(
        request,
        "personal_access_tokens.html",
        {
            "personal_access_tokens": list_personal_access_tokens(user_id),
            "raw_token": raw_token,
        },
    )
    if raw_token:
        response.headers["Cache-Control"] = "no-store"
    return response


def _pat_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A personal access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


def get_mcp_authenticated_user_id(request: Request) -> int:
    """Authenticate MCP traffic with a PAT, independently of web JWTs."""

    try:
        user_id = authenticate_personal_access_token(_pat_bearer_token(request))
    except PersonalAccessTokenError as exc:
        logger.warning("mcp.authentication.failed reason=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    request.state.authenticated_user_id = user_id
    logger.info("mcp.authentication.succeeded user_id=%s", user_id)
    return user_id


def get_conversation_api_user_id(request: Request) -> int:
    """Allow web JWT identity or PAT identity for conversation discovery."""

    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer ipt_pat_"):
        return get_mcp_authenticated_user_id(request)
    return get_authenticated_user_id(request)


@router.post("/api/v1/personal-access-tokens", status_code=status.HTTP_201_CREATED)
def create_pat(
    payload: PersonalAccessTokenCreate,
    user_id: int = Depends(get_jwt_bearer_user_id),
):
    try:
        issued = create_personal_access_token(user_id, payload.name, payload.expires_at)
    except PersonalAccessTokenError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "token_id": issued.token_id,
        "name": issued.name,
        "expires_at": issued.expires_at,
        "token": issued.token,
    }


@router.get(
    "/settings/personal-access-tokens",
    name="personal_access_tokens_page",
)
def personal_access_tokens_page(request: Request):
    user_id = get_authenticated_user_id(request)
    return _render_pat_page(request, user_id)


@router.post(
    "/settings/personal-access-tokens",
    name="create_personal_access_token_page",
)
async def create_personal_access_token_page(request: Request):
    user_id = get_authenticated_user_id(request)
    form = await request.form()
    validate_csrf_token(request, form.get("csrf_token"))
    try:
        issued = create_personal_access_token(
            user_id,
            str(form.get("name", "")),
            str(form.get("expires_at", "")).strip() or None,
        )
    except PersonalAccessTokenError as exc:
        flash_message(request, str(exc), "danger")
        return redirect_to(request, "personal_access_tokens_page")

    # Render directly: the raw PAT must never enter redirect or session state.
    return _render_pat_page(request, user_id, raw_token=issued.token)


@router.post(
    "/settings/personal-access-tokens/{token_id}/revoke",
    name="revoke_personal_access_token_page",
)
async def revoke_personal_access_token_page(request: Request, token_id: int):
    user_id = get_authenticated_user_id(request)
    form = await request.form()
    validate_csrf_token(request, form.get("csrf_token"))
    revoked = revoke_personal_access_token(token_id, user_id)
    flash_message(
        request,
        "Personal access token revoked." if revoked else "Personal access token not found.",
        "success" if revoked else "danger",
    )
    return redirect_to(request, "personal_access_tokens_page")


@router.get("/api/v1/personal-access-tokens")
def list_pats(user_id: int = Depends(get_jwt_bearer_user_id)):
    return list_personal_access_tokens(user_id)


@router.delete("/api/v1/personal-access-tokens/{token_id}", status_code=204)
def revoke_pat(token_id: int, user_id: int = Depends(get_jwt_bearer_user_id)):
    if not revoke_personal_access_token(token_id, user_id):
        raise HTTPException(status_code=404, detail="Personal access token not found.")
    return Response(status_code=204)


@router.get("/api/v1/conversations")
def list_conversations(user_id: int = Depends(get_conversation_api_user_id)):
    return chat_service.list_conversations(user_id)


@router.api_route("/mcp/sse", methods=["GET", "POST", "DELETE"])
async def mcp_transport(
    request: Request,
    user_id: int = Depends(get_mcp_authenticated_user_id),
):
    if request.method == "GET" and not request.headers.get("mcp-session-id"):
        return await open_sse_connection(request, user_id)
    return await handle_streamable_http(request, user_id)


@router.post("/mcp/messages")
async def mcp_messages(
    request: Request,
    user_id: int = Depends(get_mcp_authenticated_user_id),
):
    return await handle_sse_message(request, user_id)
