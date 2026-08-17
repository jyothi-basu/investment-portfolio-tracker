"""Route registration package for the Flask application."""

from .auth import register_routes as register_auth_routes
from .portfolio import register_routes as register_portfolio_routes
from .chat import register_routes as register_chat_routes


def register_routes(app):
    register_auth_routes(app)
    register_portfolio_routes(app)
    register_chat_routes(app)
