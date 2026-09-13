"""Trusted-context wrappers around read-only portfolio services."""

from langchain_core.tools import tool

from app.ai.context import get_trusted_user_id
from app.services import portfolio_service

from .common import json_content


def get_portfolio_summary_for_user(user_id):
    return portfolio_service.calculate_portfolio_summary(user_id)


def get_holdings_for_user(user_id):
    return portfolio_service.calculate_holdings_by_symbol(user_id)


def get_transactions_for_user(user_id):
    return [
        {
            "symbol": row["stock_symbol"],
            "transaction_type": row["transaction_type"],
            "quantity": int(row["quantity"]),
            "price": float(row["price_per_share"]),
            "transaction_date": row["transaction_date"],
            "demat_account": row["broker_name"],
        }
        for row in portfolio_service.fetch_transactions(user_id)
    ]


def get_stock_prices_for_user(user_id):
    return portfolio_service.fetch_prices(user_id)


def get_demat_accounts_for_user(user_id):
    return [
        {
            "demat_account": row["broker_name"],
            "broker_name": row["broker_name"],
        }
        for row in portfolio_service.fetch_accounts(user_id)
    ]


@tool("get_portfolio_summary")
def get_portfolio_summary() -> str:
    """Return the authenticated user's portfolio summary."""

    return json_content(get_portfolio_summary_for_user(get_trusted_user_id()))


@tool("get_holdings")
def get_holdings() -> str:
    """Return the authenticated user's current holdings."""

    return json_content(get_holdings_for_user(get_trusted_user_id()))


@tool("get_transactions")
def get_transactions() -> str:
    """Return the authenticated user's transactions."""

    return json_content(get_transactions_for_user(get_trusted_user_id()))


@tool("get_stock_prices")
def get_stock_prices() -> str:
    """Return the authenticated user's stored stock prices."""

    return json_content(get_stock_prices_for_user(get_trusted_user_id()))


@tool("get_demat_accounts")
def get_demat_accounts() -> str:
    """Return the authenticated user's demat accounts."""

    return json_content(get_demat_accounts_for_user(get_trusted_user_id()))


PORTFOLIO_ASSISTANT_TOOLS = (
    get_portfolio_summary,
    get_holdings,
    get_transactions,
    get_stock_prices,
    get_demat_accounts,
)
