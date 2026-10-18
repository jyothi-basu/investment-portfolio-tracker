"""Phase 1 tests for SQLAlchemy database configuration and ORM metadata."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.repository import database
from app.repository.models import (
    Base,
    Chat,
    ChatMessage,
    DematAccount,
    Document,
    StockPrice,
    Transaction,
    User,
)
from tests.database_helpers import (
    cleanup_test_database,
    configure_test_database,
    get_test_database_url,
)


@pytest.fixture
def test_engine():
    configure_test_database()
    engine = database.get_engine()
    try:
        yield engine
    finally:
        cleanup_test_database()


def test_database_url_is_required_when_not_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        database.get_database_url()


def test_explicit_sqlalchemy_engine_connects(test_engine):
    engine = test_engine
    try:
        with engine.connect() as connection:
            assert connection.dialect.name == make_url(get_test_database_url()).get_backend_name()
    finally:
        engine.dispose()


def test_orm_metadata_can_create_current_schema_on_explicit_test_database(test_engine):
    engine = test_engine
    try:
        Base.metadata.create_all(engine)
        assert set(Base.metadata.tables) == {
            "users",
            "refresh_tokens",
            "personal_access_tokens",
            "demat_accounts",
            "transactions",
            "stock_prices",
            "chats",
            "chat_messages",
            "documents",
        }
        with sessionmaker(bind=engine, expire_on_commit=False)() as session:
            session.add(User(username="ORM User", email="orm@example.com", password_hash="hash"))
            session.commit()
    finally:
        engine.dispose()


def test_models_preserve_indexes_foreign_keys_and_money_precision():
    assert len(Base.metadata.tables["transactions"].foreign_keys) == 1
    assert len(Base.metadata.tables["documents"].foreign_keys) == 1
    assert {index.name for index in Base.metadata.tables["documents"].indexes} == {
        "idx_documents_chat_id",
    }

    transaction_price = Base.metadata.tables["transactions"].c.price_per_share.type
    stock_price = Base.metadata.tables["stock_prices"].c.current_price.type
    assert transaction_price.precision == 18
    assert transaction_price.scale == 4
    assert stock_price.precision == 18
    assert stock_price.scale == 4


def test_relationships_and_user_cascade_work_on_postgresql(test_engine):
    engine = test_engine
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        with Session() as session:
            user = User(username="Cascade User", email="cascade@example.com", password_hash="hash")
            account = DematAccount(broker_name="Broker", user=user)
            account.transactions.append(
                Transaction(
                    stock_symbol="ABC",
                    transaction_type="BUY",
                    quantity=2,
                    price_per_share=Decimal("10.2500"),
                    transaction_date=date(2026, 1, 1),
                )
            )
            user.stock_prices.append(
                StockPrice(stock_symbol="ABC", current_price=Decimal("11.5000"))
            )
            chat = Chat(conversation_id="conversation-1", title="Research", user=user)
            chat.messages.append(ChatMessage(role="USER", content="Show my holdings"))
            chat.documents.append(
                Document(
                    original_filename="report.pdf",
                    processing_status="COMPLETED",
                )
            )
            session.add(user)
            session.commit()
            user_id = user.user_id

            assert user.demat_accounts[0].transactions[0].price_per_share == Decimal("10.2500")

            session.delete(user)
            session.commit()

            assert session.get(User, user_id) is None
            assert session.query(DematAccount).count() == 0
            assert session.query(Transaction).count() == 0
            assert session.query(StockPrice).count() == 0
            assert session.query(Chat).count() == 0
            assert session.query(ChatMessage).count() == 0
            assert session.query(Document).count() == 0
    finally:
        engine.dispose()


def test_model_constraints_reject_duplicate_prices_and_invalid_values(test_engine):
    engine = test_engine
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        with Session() as session:
            user = User(username="Constraint User", email="constraint@example.com", password_hash="hash")
            session.add(user)
            session.commit()

            session.add_all(
                [
                    StockPrice(user_id=user.user_id, stock_symbol="ABC", current_price=Decimal("1.0000")),
                    StockPrice(user_id=user.user_id, stock_symbol="ABC", current_price=Decimal("2.0000")),
                ]
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            chat = Chat(user_id=user.user_id, conversation_id="conversation-2")
            session.add(chat)
            session.commit()
            session.add(ChatMessage(chat_id=chat.chat_id, role="SYSTEM", content="not allowed"))
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_domain_constraints_reject_invalid_transactions_and_duplicate_usernames(test_engine):
    engine = test_engine
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        with Session() as session:
            user = User(username="Unique User", email="unique@example.com", password_hash="hash")
            account = DematAccount(broker_name="Broker", user=user)
            session.add(user)
            session.commit()

            session.add(User(username="Unique User", email="other@example.com", password_hash="hash"))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            invalid_transactions = (
                Transaction(
                    account_id=account.account_id,
                    stock_symbol="ABC",
                    transaction_type="BUYY",
                    quantity=1,
                    price_per_share=Decimal("10.0000"),
                    transaction_date=date(2026, 1, 1),
                ),
                Transaction(
                    account_id=account.account_id,
                    stock_symbol="ABC",
                    transaction_type="BUY",
                    quantity=0,
                    price_per_share=Decimal("10.0000"),
                    transaction_date=date(2026, 1, 1),
                ),
                Transaction(
                    account_id=account.account_id,
                    stock_symbol="ABC",
                    transaction_type="BUY",
                    quantity=1,
                    price_per_share=Decimal("0.0000"),
                    transaction_date=date(2026, 1, 1),
                ),
            )
            for invalid_transaction in invalid_transactions:
                session.add(invalid_transaction)
                with pytest.raises(IntegrityError):
                    session.commit()
                session.rollback()

            session.add(
                StockPrice(
                    user_id=user.user_id,
                    stock_symbol="ABC",
                    current_price=Decimal("0.0000"),
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_document_ownership_is_derived_from_chat_owner(test_engine):
    engine = test_engine
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        with Session() as session:
            owner = User(username="Owner", email="owner@example.com", password_hash="hash")
            chat = Chat(conversation_id="owned-conversation", user=owner)
            session.add_all([owner, chat])
            session.commit()

            document = Document(
                chat=chat,
                original_filename="owned.pdf",
                processing_status="UPLOADED",
            )
            session.add(document)
            session.commit()

            assert "user_id" not in Document.__table__.c
            assert document.chat.user_id == owner.user_id
    finally:
        engine.dispose()


def test_timestamps_are_utc_aware_and_chat_updates_refresh_updated_at(test_engine):
    engine = test_engine
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        with Session() as session:
            user = User(username="Time User", email="time@example.com", password_hash="hash")
            chat = Chat(conversation_id="time-conversation", user=user)
            session.add(chat)
            session.commit()

            assert chat.created_at.tzinfo is not None
            assert chat.updated_at.tzinfo is not None
            original_updated_at = chat.updated_at

            chat.title = "Updated title"
            session.commit()

            assert chat.updated_at >= original_updated_at
            assert chat.updated_at.tzinfo is not None
    finally:
        engine.dispose()
