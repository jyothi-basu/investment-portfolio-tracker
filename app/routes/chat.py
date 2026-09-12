"""Chat routes for persistent conversations and assistant requests."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.ai.chat import ChatServiceError
from app.ai.orchestrator import generate_chat_response
from app.routes.auth import get_optional_user_id, validate_csrf_token
from app.routes.common import flash_message, parse_int, redirect_to, render_template
from app.services import chat_service
from app.services.chat_title_service import generate_title_if_needed
from app.services import document_service


router = APIRouter()


def _build_history(history_rows):
    return [
        {"role": row["role"].lower(), "content": row["content"]}
        for row in history_rows[-10:]
    ]


@router.api_route("/chat", methods=["GET", "POST"])
async def chat_page(request: Request):
    user_id = get_optional_user_id(request)
    if user_id is None:
        flash_message(request, "Please log in to continue.", "warning")
        return redirect_to(request, "home")

    chats = chat_service.list_chats(user_id)
    selected_chat_id = parse_int(request.query_params.get("chat_id")) or parse_int(
        request.session.get("active_chat_id")
    )
    user_message = ""
    assistant_reply = ""

    if not chats:
        new_chat_id = chat_service.create_chat(user_id)
        request.session["active_chat_id"] = new_chat_id
        return redirect_to(request, "chat_page", chat_id=new_chat_id)

    if request.method == "POST":
        form = await request.form()
        validate_csrf_token(request, form.get("csrf_token"))
        action = str(form.get("action", "send_message")).strip().lower()
        posted_chat_id = parse_int(form.get("chat_id"))
        if posted_chat_id is not None:
            selected_chat_id = posted_chat_id

        if action == "create_chat":
            new_chat_id = chat_service.create_chat(user_id)
            request.session["active_chat_id"] = new_chat_id
            return redirect_to(request, "chat_page", chat_id=new_chat_id)

        if action == "upload_document":
            if selected_chat_id is None:
                selected_chat_id = chats[0]["chat_id"]
            uploaded_file = form.get("document")
            ok, message, _document_id = document_service.upload_document(
                selected_chat_id,
                user_id,
                uploaded_file,
            )
            flash_message(request, message, "success" if ok else "danger")
            if ok:
                chat_service.touch_chat(selected_chat_id)
                request.session["active_chat_id"] = selected_chat_id
            return redirect_to(request, "chat_page", chat_id=selected_chat_id)

        if selected_chat_id is None:
            selected_chat_id = chats[0]["chat_id"]

        selected_chat = chat_service.get_chat(selected_chat_id, user_id)
        if not selected_chat:
            flash_message(request, "Chat not found.", "danger")
            return redirect_to(request, "chat_page")

        user_message = str(form.get("message", "")).strip()
        if not user_message:
            flash_message(request, "Please enter a message.", "danger")
        else:
            history_rows = chat_service.list_messages(selected_chat_id, user_id)
            history = _build_history(history_rows)
            try:
                chat_service.add_user_message(selected_chat_id, user_message)
                generate_title_if_needed(selected_chat_id, user_id, user_message)
                assistant_reply = generate_chat_response(
                    user_message=user_message,
                    user_id=user_id,
                    chat_id=selected_chat_id,
                    history=history,
                )
                chat_service.add_assistant_message(selected_chat_id, assistant_reply)
                chat_service.touch_chat(selected_chat_id)
                request.session["active_chat_id"] = selected_chat_id
                return redirect_to(request, "chat_page", chat_id=selected_chat_id)
            except ChatServiceError as exc:
                flash_message(request, str(exc), "danger")

    if selected_chat_id is None:
        selected_chat_id = chats[0]["chat_id"]

    selected_chat = chat_service.get_chat(selected_chat_id, user_id)
    if not selected_chat:
        flash_message(request, "Chat not found.", "danger")
        return redirect_to(request, "chat_page", chat_id=chats[0]["chat_id"])

    messages = chat_service.list_messages(selected_chat_id, user_id)
    documents = document_service.list_documents_for_chat(selected_chat_id, user_id)
    request.session["active_chat_id"] = selected_chat_id
    return render_template(
        request,
        "chat.html",
        {
            "chats": chats,
            "selected_chat": selected_chat,
            "messages": messages,
            "documents": documents,
            "user_message": user_message,
            "assistant_reply": assistant_reply,
            "active_chat_id": selected_chat_id,
        },
    )


@router.post("/chat/delete/{chat_id}")
async def delete_chat(request: Request, chat_id: int):
    user_id = get_optional_user_id(request)
    if user_id is None:
        flash_message(request, "Please log in to continue.", "warning")
        return redirect_to(request, "home")

    form = await request.form()
    validate_csrf_token(request, form.get("csrf_token"))
    ok, message = chat_service.delete_chat(chat_id, user_id)
    if ok and request.session.get("active_chat_id") == chat_id:
        request.session.pop("active_chat_id", None)
    flash_message(request, message, "success" if ok else "danger")
    return redirect_to(request, "chat_page")
