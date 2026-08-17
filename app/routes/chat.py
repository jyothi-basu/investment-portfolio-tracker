"""Chat routes for persistent conversations and document attachment management."""

from flask import flash, redirect, render_template, request, session, url_for

from app.ai.chat import ChatServiceError
from app.ai.orchestrator import generate_chat_response
from app.routes.common import login_required
from app.routes.common import parse_int
from app.services import document_service
from app.services import chat_service


def register_routes(app):
    @app.route("/chat", methods=["GET", "POST"])
    @login_required
    def chat_page():
        user_id = session["user_id"]
        chats = chat_service.list_chats(user_id)
        selected_chat_id = parse_int(request.args.get("chat_id")) or parse_int(session.get("active_chat_id"))
        user_message = ""
        assistant_reply = ""

        if not chats:
            new_chat_id = chat_service.create_chat(user_id)
            session["active_chat_id"] = new_chat_id
            return redirect(url_for("chat_page", chat_id=new_chat_id))

        if request.method == "POST":
            action = request.form.get("action", "send_message").strip().lower()
            posted_chat_id = parse_int(request.form.get("chat_id"))
            if posted_chat_id is not None:
                selected_chat_id = posted_chat_id

            if action == "create_chat":
                new_chat_id = chat_service.create_chat(user_id)
                session["active_chat_id"] = new_chat_id
                return redirect(url_for("chat_page", chat_id=new_chat_id))

            if action == "upload_document":
                if selected_chat_id is None:
                    selected_chat_id = chats[0]["chat_id"]
                uploaded_file = request.files.get("document")
                ok, message, document_id = document_service.upload_document(
                    selected_chat_id,
                    user_id,
                    uploaded_file,
                )
                flash(message, "success" if ok else "danger")
                if ok:
                    chat_service.touch_chat(selected_chat_id)
                    session["active_chat_id"] = selected_chat_id
                    return redirect(url_for("chat_page", chat_id=selected_chat_id))
                return redirect(url_for("chat_page", chat_id=selected_chat_id))

            if selected_chat_id is None:
                selected_chat_id = chats[0]["chat_id"]

            selected_chat = chat_service.get_chat(selected_chat_id, user_id)
            if not selected_chat:
                flash("Chat not found.", "danger")
                return redirect(url_for("chat_page"))

            user_message = request.form.get("message", "").strip()
            if not user_message:
                flash("Please enter a message.", "danger")
            else:
                history_rows = chat_service.list_messages(selected_chat_id, user_id)
                history = [
                    {"role": row["role"].lower(), "content": row["content"]}
                    for row in history_rows[-10:]
                ]
                try:
                    chat_service.add_user_message(selected_chat_id, user_message)
                    assistant_reply = generate_chat_response(
                        user_message=user_message,
                        user_id=user_id,
                        chat_id=selected_chat_id,
                        history=history,
                    )
                    chat_service.add_assistant_message(selected_chat_id, assistant_reply)
                    chat_service.touch_chat(selected_chat_id)
                    session["active_chat_id"] = selected_chat_id
                    return redirect(url_for("chat_page", chat_id=selected_chat_id))
                except ChatServiceError as exc:
                    flash(str(exc), "danger")

        if selected_chat_id is None:
            selected_chat_id = chats[0]["chat_id"]

        selected_chat = chat_service.get_chat(selected_chat_id, user_id)
        if not selected_chat:
            flash("Chat not found.", "danger")
            return redirect(url_for("chat_page", chat_id=chats[0]["chat_id"]))

        messages = chat_service.list_messages(selected_chat_id, user_id)
        documents = document_service.list_documents_for_chat(selected_chat_id, user_id)
        session["active_chat_id"] = selected_chat_id
        return render_template(
            "chat.html",
            chats=chats,
            selected_chat=selected_chat,
            messages=messages,
            documents=documents,
            user_message=user_message,
            assistant_reply=assistant_reply,
            active_chat_id=selected_chat_id,
        )

    @app.route("/chat/delete/<int:chat_id>", methods=["POST"])
    @login_required
    def delete_chat(chat_id):
        ok, message = chat_service.delete_chat(chat_id, session["user_id"])
        if ok and session.get("active_chat_id") == chat_id:
            session.pop("active_chat_id", None)
        flash(message, "success" if ok else "danger")
        return redirect(url_for("chat_page"))

    @app.route("/chat/documents/delete/<int:document_id>", methods=["POST"])
    @login_required
    def delete_document(document_id):
        ok, message = document_service.delete_document(document_id, session["user_id"])
        flash(message, "success" if ok else "danger")
        return redirect(url_for("chat_page"))
