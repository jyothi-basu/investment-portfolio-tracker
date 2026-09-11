"""Public pages plus JWT login, refresh, registration, and logout routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.routes.auth import (
    REFRESH_TOKEN_COOKIE,
    clear_auth_cookies,
    set_auth_cookies,
    validate_csrf_token,
)
from app.routes.common import flash_message, redirect_to, render_template
from app.security.jwt import TokenValidationError
from app.services import auth_service, portfolio_service


router = APIRouter()


@router.get("/", name="home")
def home(request: Request):
    return render_template(request, "home.html")


@router.api_route("/register", methods=["GET", "POST"], name="register")
async def register(request: Request):
    if request.method == "POST":
        form = await request.form()
        validate_csrf_token(request, form.get("csrf_token"))
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
        validate_csrf_token(request, form.get("csrf_token"))
        email = str(form.get("email", "")).strip().lower()
        password = str(form.get("password", ""))
        user = portfolio_service.authenticate_user(email, password)

        if not user:
            flash_message(request, "Invalid email or password.", "danger")
        else:
            pair = auth_service.issue_token_pair(user["user_id"])
            request.session.pop("active_chat_id", None)
            flash_message(request, "Welcome back.", "success")
            response = redirect_to(request, "dashboard_page")
            request.state.suppress_auth_cookie_update = True
            set_auth_cookies(response, pair)
            return response

    return render_template(request, "login.html")


@router.post("/auth/refresh", name="refresh_access_token")
async def refresh_access_token(request: Request):
    form = await request.form()
    validate_csrf_token(request, form.get("csrf_token"))
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A refresh token is required.",
        )
    try:
        pair = auth_service.rotate_refresh_token(refresh_token)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The refresh token is invalid or expired.",
        ) from exc
    response = JSONResponse({"message": "Authentication tokens refreshed."})
    request.state.suppress_auth_cookie_update = True
    set_auth_cookies(response, pair)
    return response


@router.post("/logout", name="logout")
async def logout(request: Request):
    form = await request.form()
    validate_csrf_token(request, form.get("csrf_token"))
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if refresh_token:
        auth_service.revoke_refresh_token(refresh_token)
    request.session.clear()
    flash_message(request, "You have been logged out.", "info")
    response = redirect_to(request, "home")
    request.state.suppress_auth_cookie_update = True
    clear_auth_cookies(response)
    return response
