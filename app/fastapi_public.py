"""FastAPI routes for the public pages and authentication flow.

This module replaces the Flask-only home, register, login, and logout routes
with FastAPI equivalents so the browser flow works end to end during migration.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.fastapi_templates import flash_message, redirect_to, render_template
from app.services import portfolio_service


router = APIRouter()


@router.get("/", name="home")
def home(request: Request):
    return render_template(request, "home.html")


@router.api_route("/register", methods=["GET", "POST"], name="register")
async def register(request: Request):
    if request.method == "POST":
        form = await request.form()
        username = str(form.get("username", "")).strip()
        email = str(form.get("email", "")).strip().lower()
        password = str(form.get("password", ""))

        if not username or not email or not password:
            flash_message(request, "All fields are required.", "danger")
        elif len(password) < 8:
            flash_message(
                request,
                "Password must be at least 8 characters long.",
                "danger",
            )
        else:
            ok, message = portfolio_service.register_user(username, email, password)
            flash_message(request, message, "success" if ok else "danger")
            if ok:
                return redirect_to(request, "login")

    return render_template(request, "register.html")


@router.api_route("/login", methods=["GET", "POST"], name="login")
async def login(request: Request):
    if request.method == "POST":
        form = await request.form()
        email = str(form.get("email", "")).strip().lower()
        password = str(form.get("password", ""))

        user = portfolio_service.authenticate_user(email, password)

        if not user:
            flash_message(request, "Invalid email or password.", "danger")
        else:
            request.session.clear()
            request.session["user_id"] = user["user_id"]
            flash_message(request, "Welcome back.", "success")
            return redirect_to(request, "dashboard_page")

    return render_template(request, "login.html")


@router.get("/logout", name="logout")
def logout(request: Request):
    request.session.clear()
    flash_message(request, "You have been logged out.", "info")
    return redirect_to(request, "home")