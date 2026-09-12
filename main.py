"""FastAPI application entrypoint for the Investment Portfolio Tracker.

This module creates the FastAPI app, loads shared configuration, and mounts
the server-rendered web routers used by the application.
"""

from pathlib import Path
import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.routes.auth import (
    authenticate_request,
    clear_auth_cookies,
    set_auth_cookies,
)
from app.routes.chat import router as chat_router
from app.routes.documents import router as document_router
from app.routes.mcp import router as mcp_router
from app.routes.portfolio import router as portfolio_router
from app.routes.public import router as public_router
from app.repository.db import init_db
from app.mcp.session_manager import session_manager
from app.mcp.streamable_http import run_streamable_http_manager
from app.security.jwt import TokenValidationError, get_jwt_settings


load_dotenv()
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared application state before serving requests."""

    session_secret = os.environ.get("SECRET_KEY", "").strip()
    if (
        len(session_secret) < 32
        or session_secret == "change-me-to-a-random-secret"
    ):
        raise RuntimeError(
            "SECRET_KEY is required and must contain at least 32 random characters."
        )
    init_db()
    get_jwt_settings()
    logger.info(
        "fastapi.startup complete templates=%s static=%s",
        TEMPLATES_DIR,
        STATIC_DIR,
    )
    async with run_streamable_http_manager(app):
        try:
            yield
        finally:
            cleaned = session_manager.clear()
            logger.info("mcp.sessions.shutdown_cleanup count=%s", cleaned)


def create_fastapi_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Investment Portfolio Tracker",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Templates
    app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Routers
    app.include_router(public_router)
    app.include_router(portfolio_router)
    app.include_router(document_router)
    app.include_router(chat_router)
    app.include_router(mcp_router)

    # ------------------------------------------------------------------
    # Custom middleware (defined BEFORE SessionMiddleware is added)
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def jwt_authentication_middleware(
        request: Request,
        call_next,
    ):
        request.state.authenticated_user_id = None
        request.state.refreshed_tokens = None
        request.state.clear_auth_cookies = False
        request.state.suppress_auth_cookie_update = False

        try:
            authentication = authenticate_request(
                request,
                allow_refresh=request.url.path
                not in {"/login", "/logout", "/auth/refresh"},
            )
            request.state.authenticated_user_id = authentication.user_id
            request.state.refreshed_tokens = authentication.refreshed_tokens
            request.state.clear_auth_cookies = authentication.clear_cookies
        except TokenValidationError:
            # An explicitly invalid bearer token must not erase an unrelated
            # valid browser session cookie.
            request.state.authenticated_user_id = None

        response = await call_next(request)
        if request.state.suppress_auth_cookie_update:
            return response
        if request.state.refreshed_tokens:
            set_auth_cookies(response, request.state.refreshed_tokens)
        elif request.state.clear_auth_cookies:
            clear_auth_cookies(response)

        return response

    # ------------------------------------------------------------------
    # Session middleware (ADD THIS AFTER custom middleware definition)
    # ------------------------------------------------------------------
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("SECRET_KEY", "change-me-to-a-random-secret"),
        same_site="lax",
        https_only=os.environ.get("SESSION_COOKIE_SECURE", "false").lower()
        in {"1", "true", "yes", "on"},
    )

    # Health check
    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "framework": "fastapi",
            "phase": "primary",
        }

    return app


app = create_fastapi_app()
