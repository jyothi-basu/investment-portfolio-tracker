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

from app.routes.auth import bind_trusted_request_context
from app.routes.chat import router as chat_router
from app.routes.documents import router as document_router
from app.routes.portfolio import router as portfolio_router
from app.routes.public import router as public_router
from app.repository.db import init_db


load_dotenv()
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared application state before serving requests."""

    init_db()
    logger.info(
        "fastapi.startup complete templates=%s static=%s",
        TEMPLATES_DIR,
        STATIC_DIR,
    )
    yield


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
