"""FastAPI foundation for the future Flask-to-FastAPI migration.

This module mirrors the current project bootstrap so the ASGI app can share the
same environment loading, database initialization, static assets, and template
paths without moving business logic yet.
"""

from pathlib import Path
import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.fastapi_auth import bind_trusted_request_context
from app.fastapi_chat import router as chat_router
from app.fastapi_documents import router as document_router
from app.fastapi_public import router as public_router
from app.fastapi_portfolio import router as portfolio_router
from app.repository.db import init_db


load_dotenv()
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_fastapi_app() -> FastAPI:
    """Create the FastAPI application shell used during migration."""

    app = FastAPI(
        title="Investment Portfolio Tracker",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
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

    # ------------------------------------------------------------------
    # Custom middleware (defined BEFORE SessionMiddleware is added)
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def trusted_assistant_context_middleware(
        request: Request,
        call_next,
    ):
        request.state.assistant_context = None

        # SessionMiddleware will populate request.session before this runs.
        session_user_id = request.session.get("user_id")
        active_chat_id = request.session.get("active_chat_id")

        if session_user_id is not None and active_chat_id is not None:
            with bind_trusted_request_context(request) as context:
                request.state.assistant_context = context
                response = await call_next(request)
        else:
            response = await call_next(request)

        return response

    # ------------------------------------------------------------------
    # Session middleware (ADD THIS AFTER custom middleware definition)
    # ------------------------------------------------------------------
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("SECRET_KEY", "change-me-to-a-random-secret"),
        same_site="lax",
        https_only=False,  # Set True when serving over HTTPS in production.
    )

    # Startup
    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        logger.info(
            "fastapi.startup complete templates=%s static=%s",
            TEMPLATES_DIR,
            STATIC_DIR,
        )

    # Health check
    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "framework": "fastapi",
            "phase": "migration-foundation",
        }

    return app


app = create_fastapi_app()