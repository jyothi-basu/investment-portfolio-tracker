"""Maintain authenticated, process-local conversation state for MCP transports."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import RLock


@dataclass(frozen=True)
class MCPSession:
    session_id: str
    user_id: int
    active_conversation_id: str | None
    connected_at: datetime


class MCPSessionManager:
    """Store ephemeral MCP sessions without mixing them into application data."""

    def __init__(self):
        self._sessions: dict[str, MCPSession] = {}
        self._lock = RLock()

    def create(
        self,
        session_id: str,
        user_id: int,
        active_conversation_id: str | None = None,
    ) -> MCPSession:
        session = MCPSession(
            session_id=session_id,
            user_id=int(user_id),
            active_conversation_id=active_conversation_id,
            connected_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get_for_user(self, session_id: str, user_id: int) -> MCPSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
        if not session or session.user_id != int(user_id):
            return None
        return session

    def get(self, session_id: str) -> MCPSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def select_conversation(
        self,
        session_id: str,
        user_id: int,
        conversation_id: str,
    ) -> MCPSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session or session.user_id != int(user_id):
                return None
            updated = replace(session, active_conversation_id=conversation_id)
            self._sessions[session_id] = updated
            return updated

    def remove(self, session_id: str) -> MCPSession | None:
        with self._lock:
            return self._sessions.pop(session_id, None)

    def clear(self) -> int:
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
        return count


session_manager = MCPSessionManager()
