"""Flask application factory for the Investment Portfolio Tracker.

This module wires the layered application together and explicitly points Flask
at the repository-level `templates/` and `static/` directories so the package
layout does not break template resolution.
"""

from pathlib import Path
import os

from flask import Flask


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app():
    """Create and configure the Flask application instance."""

    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-to-a-random-secret")

    from app.routes.auth import register_routes as register_auth_routes
    from app.routes.chat import register_routes as register_chat_routes
    from app.routes.portfolio import register_routes as register_portfolio_routes

    register_auth_routes(app)
    register_chat_routes(app)
    register_portfolio_routes(app)

    return app
