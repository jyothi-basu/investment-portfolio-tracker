"""Unit tests for shared AI tools and trusted execution metadata."""

import json
from unittest.mock import patch

from app.ai.context import push_assistant_context
from app.ai.tools import TOOL_REGISTRY
from app.ai.tools.portfolio import get_demat_accounts, get_transactions


class TestSharedAITools:
    def test_transactions_use_trusted_user_and_business_fields(self):
        rows = [
            {
                "stock_symbol": "GOOGL",
                "transaction_type": "BUY",
                "quantity": 3,
                "price_per_share": 150.5,
                "transaction_date": "2026-01-01",
                "broker_name": "Aster Demat",
            }
        ]
        with patch("app.ai.tools.portfolio.portfolio_service.fetch_transactions", return_value=rows) as fetch:
            with push_assistant_context(user_id=7, chat_id=11):
                payload = json.loads(get_transactions.invoke({}))

        fetch.assert_called_once_with(7)
        assert payload[0]["symbol"] == "GOOGL"
        assert payload[0]["price"] == 150.5
        assert "user_id" not in payload[0]

    def test_demat_accounts_expose_human_readable_names(self):
        with patch(
            "app.ai.tools.portfolio.portfolio_service.fetch_accounts",
            return_value=[{"broker_name": "Aster Securities"}],
        ):
            with push_assistant_context(user_id=7, chat_id=11):
                payload = json.loads(get_demat_accounts.invoke({}))

        assert payload == [{"demat_account": "Aster Securities", "broker_name": "Aster Securities"}]

    def test_registry_declares_execution_policy_for_all_shared_tools(self):
        assert len(TOOL_REGISTRY) == 7
        for spec in TOOL_REGISTRY.values():
            assert spec.read_only
            assert spec.parallel_safe
            assert spec.category in {"portfolio", "documents", "application"}
