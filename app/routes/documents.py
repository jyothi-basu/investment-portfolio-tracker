"""Document upload and deletion routes for the web application."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.routes.auth import get_optional_user_id, validate_csrf_token
from app.routes.common import flash_message, parse_int
from app.services import chat_service
from app.services import document_service


router = APIRouter()


def _redirect_back(request: Request):
    referer = request.headers.get("referer")
    if referer:
        return RedirectResponse(url=referer, status_code=303)
    return RedirectResponse(url=request.url_for("home"), status_code=303)


def _resolve_chat_id(request: Request, chat_id):
    resolved = parse_int(chat_id)
    if resolved is not None:
        return resolved
    return parse_int(request.session.get("active_chat_id"))


@router.post("/chat/documents/upload")
async def upload_document(
    request: Request,
    chat_id: str = Form(""),
    csrf_token: str = Form(""),
    document: UploadFile = File(...),
):
    user_id = get_optional_user_id(request)
    if user_id is None:
        flash_message(request, "Please log in to continue.", "warning")
        return _redirect_back(request)

    validate_csrf_token(request, csrf_token)
    selected_chat_id = _resolve_chat_id(request, chat_id)
    if selected_chat_id is None:
        flash_message(request, "Please select a chat before uploading a document.", "danger")
        return _redirect_back(request)

    ok, message, _document_id = document_service.upload_document(
        selected_chat_id,
        user_id,
        document,
    )
    flash_message(request, message, "success" if ok else "danger")
    if ok:
        chat_service.touch_chat(selected_chat_id)
        request.session["active_chat_id"] = selected_chat_id
    return _redirect_back(request)


@router.post("/chat/documents/delete/{document_id}")
async def delete_document(request: Request, document_id: int):
    user_id = get_optional_user_id(request)
    if user_id is None:
        flash_message(request, "Please log in to continue.", "warning")
        return _redirect_back(request)

    form = await request.form()
    validate_csrf_token(request, form.get("csrf_token"))
    ok, message = document_service.delete_document(document_id, user_id)
    flash_message(request, message, "success" if ok else "danger")
    return _redirect_back(request)
