"""SQLAlchemy repository for portfolio accounts, transactions, and prices."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import case, delete, func, literal, select, update

from app.repository.models import DematAccount, StockPrice, Transaction, utc_now
from app.repository.serialization import model_to_dict, row_to_dict
from app.repository.session import session_scope


def _as_date(value: date | str) -> date:
    return date.fromisoformat(value) if isinstance(value, str) else value


def _as_decimal(value: Decimal | float | int) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def fetch_accounts(user_id: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        accounts = session.scalars(
            select(DematAccount)
            .where(DematAccount.user_id == user_id)
            .order_by(DematAccount.broker_name)
        ).all()
        return [model_to_dict(account) for account in accounts]


def fetch_account(account_id: int, user_id: int) -> dict[str, Any] | None:
    with session_scope() as session:
        account = session.scalar(
            select(DematAccount).where(
                DematAccount.account_id == account_id,
                DematAccount.user_id == user_id,
            )
        )
        return model_to_dict(account) if account is not None else None


def create_account(user_id: int, broker_name: str) -> int:
    with session_scope() as session:
        account = DematAccount(user_id=user_id, broker_name=broker_name)
        session.add(account)
        session.flush()
        return account.account_id


def update_account(account_id: int, broker_name: str) -> int:
    with session_scope() as session:
        result = session.execute(
            update(DematAccount)
            .where(DematAccount.account_id == account_id)
            .values(broker_name=broker_name)
        )
        return result.rowcount


def delete_account(account_id: int) -> int:
    with session_scope() as session:
        result = session.execute(
            delete(DematAccount).where(DematAccount.account_id == account_id)
        )
        return result.rowcount


def _transaction_columns():
    return (
        Transaction.transaction_id,
        Transaction.account_id,
        Transaction.stock_symbol,
        Transaction.transaction_type,
        Transaction.quantity,
        Transaction.price_per_share,
        Transaction.transaction_date,
    )


def fetch_transactions(user_id: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.execute(
            select(*_transaction_columns(), DematAccount.broker_name)
            .join(DematAccount, DematAccount.account_id == Transaction.account_id)
            .where(DematAccount.user_id == user_id)
            .order_by(Transaction.transaction_date.desc(), Transaction.transaction_id.desc())
        ).all()
        return [row_to_dict(row) for row in rows]


def fetch_transaction(transaction_id: int, user_id: int) -> dict[str, Any] | None:
    with session_scope() as session:
        row = session.execute(
            select(*_transaction_columns())
            .join(DematAccount, DematAccount.account_id == Transaction.account_id)
            .where(
                Transaction.transaction_id == transaction_id,
                DematAccount.user_id == user_id,
            )
        ).first()
        return row_to_dict(row) if row is not None else None


def create_transaction(
    account_id: int,
    stock_symbol: str,
    transaction_type: str,
    quantity: int,
    price_per_share: Decimal | float | int,
    transaction_date: date | str,
) -> int:
    with session_scope() as session:
        transaction = Transaction(
            account_id=account_id,
            stock_symbol=stock_symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            price_per_share=_as_decimal(price_per_share),
            transaction_date=_as_date(transaction_date),
        )
        session.add(transaction)
        session.flush()
        return transaction.transaction_id


def update_transaction(
    transaction_id: int,
    account_id: int,
    stock_symbol: str,
    transaction_type: str,
    quantity: int,
    price_per_share: Decimal | float | int,
    transaction_date: date | str,
) -> int:
    with session_scope() as session:
        result = session.execute(
            update(Transaction)
            .where(Transaction.transaction_id == transaction_id)
            .values(
                account_id=account_id,
                stock_symbol=stock_symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                price_per_share=_as_decimal(price_per_share),
                transaction_date=_as_date(transaction_date),
            )
        )
        return result.rowcount


def delete_transaction(transaction_id: int) -> int:
    with session_scope() as session:
        result = session.execute(
            delete(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        return result.rowcount


def fetch_account_stock_quantity(
    account_id: int,
    symbol: str,
    exclude_transaction_id: int | None = None,
) -> int:
    quantity_expression = func.coalesce(
        func.sum(
            case(
                (Transaction.transaction_type == "BUY", Transaction.quantity),
                else_=-Transaction.quantity,
            )
        ),
        0,
    )
    statement = select(quantity_expression).where(
        Transaction.account_id == account_id,
        func.upper(Transaction.stock_symbol) == func.upper(symbol),
    )
    if exclude_transaction_id is not None:
        statement = statement.where(Transaction.transaction_id != exclude_transaction_id)
    with session_scope() as session:
        return int(session.scalar(statement) or 0)


def fetch_prices(user_id: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        prices = session.scalars(
            select(StockPrice)
            .where(StockPrice.user_id == user_id)
            .order_by(StockPrice.stock_symbol)
        ).all()
        return [model_to_dict(price) for price in prices]


def save_price(
    user_id: int,
    stock_symbol: str,
    current_price: Decimal | float | int,
) -> int:
    with session_scope() as session:
        price = session.scalar(
            select(StockPrice).where(
                StockPrice.user_id == user_id,
                StockPrice.stock_symbol == stock_symbol,
            )
        )
        if price is None:
            price = StockPrice(
                user_id=user_id,
                stock_symbol=stock_symbol,
                current_price=_as_decimal(current_price),
            )
            session.add(price)
        else:
            price.current_price = _as_decimal(current_price)
            price.last_updated = utc_now()
        session.flush()
        return price.price_id


def _holding_quantity_expression():
    return func.sum(
        case(
            (Transaction.transaction_type == "BUY", Transaction.quantity),
            else_=-Transaction.quantity,
        )
    )


def fetch_holding_rows_by_symbol(user_id: int) -> list[dict[str, Any]]:
    symbol = func.upper(Transaction.stock_symbol).label("stock_symbol")
    quantity = _holding_quantity_expression().label("quantity")
    current_price = func.max(
        func.coalesce(StockPrice.current_price, literal(0))
    ).label("current_price")
    with session_scope() as session:
        rows = session.execute(
            select(symbol, quantity, current_price)
            .join(DematAccount, DematAccount.account_id == Transaction.account_id)
            .outerjoin(
                StockPrice,
                (StockPrice.user_id == DematAccount.user_id)
                & (func.upper(StockPrice.stock_symbol) == func.upper(Transaction.stock_symbol)),
            )
            .where(DematAccount.user_id == user_id)
            .group_by(symbol)
            .having(quantity > 0)
            .order_by(symbol)
        ).all()
        return [row_to_dict(row) for row in rows]


def fetch_holding_rows_by_account(user_id: int) -> list[dict[str, Any]]:
    symbol = func.upper(Transaction.stock_symbol).label("stock_symbol")
    quantity = _holding_quantity_expression().label("quantity")
    current_price = func.max(
        func.coalesce(StockPrice.current_price, literal(0))
    ).label("current_price")
    investment_value = func.sum(
        case(
            (
                Transaction.transaction_type == "BUY",
                Transaction.quantity * Transaction.price_per_share,
            ),
            else_=-Transaction.quantity * Transaction.price_per_share,
        )
    ).label("investment_value")
    with session_scope() as session:
        rows = session.execute(
            select(
                DematAccount.account_id,
                DematAccount.broker_name,
                symbol,
                quantity,
                current_price,
                investment_value,
            )
            .join(DematAccount, DematAccount.account_id == Transaction.account_id)
            .outerjoin(
                StockPrice,
                (StockPrice.user_id == DematAccount.user_id)
                & (func.upper(StockPrice.stock_symbol) == func.upper(Transaction.stock_symbol)),
            )
            .where(DematAccount.user_id == user_id)
            .group_by(DematAccount.account_id, DematAccount.broker_name, symbol)
            .order_by(DematAccount.broker_name, symbol)
        ).all()
        return [row_to_dict(row) for row in rows]


def fetch_total_investment_row(user_id: int) -> dict[str, Any]:
    total_investment = func.coalesce(
        func.sum(
            case(
                (
                    Transaction.transaction_type == "BUY",
                    Transaction.quantity * Transaction.price_per_share,
                ),
                else_=-Transaction.quantity * Transaction.price_per_share,
            )
        ),
        literal(0),
    ).label("total_investment")
    with session_scope() as session:
        row = session.execute(
            select(total_investment)
            .join(DematAccount, DematAccount.account_id == Transaction.account_id)
            .where(DematAccount.user_id == user_id)
        ).first()
        return row_to_dict(row) if row is not None else {"total_investment": 0.0}


def fetch_account_count(user_id: int) -> int:
    with session_scope() as session:
        return int(
            session.scalar(
                select(func.count(DematAccount.account_id)).where(
                    DematAccount.user_id == user_id
                )
            )
            or 0
        )
