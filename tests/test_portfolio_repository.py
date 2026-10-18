"""Tests for the isolated SQLAlchemy portfolio repository."""

from __future__ import annotations

import pytest

from app.repository import database
from app.repository.auth_repository import create_user
from app.repository.models import Base
from tests.database_helpers import cleanup_test_database, configure_test_database
from app.repository.portfolio_repository import (
    create_account,
    create_transaction,
    delete_transaction,
    fetch_account,
    fetch_account_count,
    fetch_account_stock_quantity,
    fetch_accounts,
    fetch_holding_rows_by_account,
    fetch_holding_rows_by_symbol,
    fetch_prices,
    fetch_total_investment_row,
    fetch_transaction,
    fetch_transactions,
    save_price,
    update_account,
    update_transaction,
)


@pytest.fixture
def portfolio_database():
    original_engine = database.engine
    original_factory = database.SessionLocal
    configure_test_database()
    try:
        yield
    finally:
        cleanup_test_database()
        database.engine = original_engine
        database.SessionLocal = original_factory


def test_portfolio_crud_and_ownership_contracts(portfolio_database):
    owner_id = create_user("Portfolio User", "portfolio@example.com", "hash")
    other_user_id = create_user("Other User", "other@example.com", "hash")
    account_id = create_account(owner_id, "Broker A")

    assert fetch_accounts(owner_id)[0]["broker_name"] == "Broker A"
    assert fetch_account(account_id, owner_id)["account_id"] == account_id
    assert fetch_account(account_id, other_user_id) is None

    assert update_account(account_id, "Broker B") == 1
    assert fetch_account(account_id, owner_id)["broker_name"] == "Broker B"

    transaction_id = create_transaction(
        account_id, "ABC", "BUY", 10, 10.25, "2026-01-01"
    )
    assert fetch_transaction(transaction_id, owner_id)["transaction_date"] == "2026-01-01"
    assert fetch_transaction(transaction_id, other_user_id) is None
    assert fetch_account_stock_quantity(account_id, "abc") == 10

    assert update_transaction(
        transaction_id, account_id, "ABC", "BUY", 12, 11.00, "2026-01-02"
    ) == 1
    assert fetch_account_stock_quantity(account_id, "ABC") == 12
    assert delete_transaction(transaction_id) == 1
    assert fetch_transactions(owner_id) == []


def test_portfolio_aggregates_match_existing_business_rules(portfolio_database):
    user_id = create_user("Aggregate User", "aggregate@example.com", "hash")
    account_id = create_account(user_id, "Broker")
    create_transaction(account_id, "ABC", "BUY", 10, 10, "2026-01-01")
    create_transaction(account_id, "ABC", "SELL", 2, 12, "2026-01-02")
    create_transaction(account_id, "XYZ", "BUY", 5, 20, "2026-01-03")
    save_price(user_id, "ABC", 11)
    save_price(user_id, "XYZ", 25)

    assert fetch_account_stock_quantity(account_id, "ABC") == 8
    assert fetch_prices(user_id)[0]["stock_symbol"] == "ABC"
    assert fetch_holding_rows_by_symbol(user_id) == [
        {
            "stock_symbol": "ABC",
            "quantity": 8,
            "current_price": 11.0,
            "valuation_price": 11.0,
        },
        {
            "stock_symbol": "XYZ",
            "quantity": 5,
            "current_price": 25.0,
            "valuation_price": 25.0,
        },
    ]
    assert fetch_total_investment_row(user_id)["total_investment"] == 176.0
    account_summary = fetch_holding_rows_by_account(user_id)
    assert account_summary[0]["investment_value"] == 76.0
    assert account_summary[1]["investment_value"] == 100.0
    assert fetch_account_count(user_id) == 1


def test_missing_current_price_uses_weighted_average_buy_price(portfolio_database):
    user_id = create_user("Fallback User", "fallback@example.com", "hash")
    account_id = create_account(user_id, "Broker")
    create_transaction(account_id, "ABC", "BUY", 10, 50, "2026-01-01")

    assert fetch_holding_rows_by_symbol(user_id) == [
        {
            "stock_symbol": "ABC",
            "quantity": 10,
            "current_price": None,
            "valuation_price": 50.0,
        }
    ]
