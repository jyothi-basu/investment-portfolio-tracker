"""MCP session isolation tests without transport or database dependencies."""

from app.mcp.session_manager import MCPSessionManager


class TestMCPSessionManager:
    def test_session_is_scoped_to_authenticated_user(self):
        manager = MCPSessionManager()
        manager.create("session-1", 10)
        assert manager.get_for_user("session-1", 10) is not None
        assert manager.get_for_user("session-1", 11) is None

    def test_conversation_selection_preserves_session_ownership(self):
        manager = MCPSessionManager()
        manager.create("session-1", 10)
        selected = manager.select_conversation("session-1", 10, "public-uuid")
        assert selected.active_conversation_id == "public-uuid"
        assert manager.select_conversation("session-1", 11, "other-uuid") is None
        assert manager.get("session-1").active_conversation_id == "public-uuid"

    def test_clear_removes_all_sessions(self):
        manager = MCPSessionManager()
        manager.create("one", 1)
        manager.create("two", 2)
        assert manager.clear() == 2
        assert manager.get("one") is None
