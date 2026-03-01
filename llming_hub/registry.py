"""Hub session registry — maps session_id to HubSessionEntry."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Dict

from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class HubSessionEntry:
    """A registered hub session with its metadata."""
    user_id: str
    user_name: str = ""
    user_email: str = ""
    user_avatar: str = ""
    locale: str = "en-us"
    websocket: Optional[WebSocket] = None
    created_at: float = field(default_factory=time.monotonic)
    last_activity: float = field(default_factory=time.monotonic)
    active_widgets: list[str] = field(default_factory=list)
    # Opaque reference to app-specific user data (e.g. O365 user instance)
    user_context: Any = None
    # Extra config passed from the page handler
    config: dict = field(default_factory=dict)
    # Set by hub_ws when WS connects
    controller: Any = None


class HubSessionRegistry:
    """Maps session_id to HubSessionEntry. Singleton."""

    _instance: Optional["HubSessionRegistry"] = None

    def __init__(self):
        self._sessions: Dict[str, HubSessionEntry] = {}

    @classmethod
    def get(cls) -> "HubSessionRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        session_id: str,
        user_id: str,
        user_name: str = "",
        user_email: str = "",
        user_avatar: str = "",
        locale: str = "en-us",
        active_widgets: list[str] | None = None,
        user_context: Any = None,
        config: dict | None = None,
    ) -> HubSessionEntry:
        entry = HubSessionEntry(
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            user_avatar=user_avatar,
            locale=locale,
            active_widgets=active_widgets or [],
            user_context=user_context,
            config=config or {},
        )
        self._sessions[session_id] = entry
        logger.info(f"[HUB_REGISTRY] Registered session {session_id} for user {user_id}")
        return entry

    def get_session(self, session_id: str) -> Optional[HubSessionEntry]:
        entry = self._sessions.get(session_id)
        if entry:
            entry.last_activity = time.monotonic()
        return entry

    def remove(self, session_id: str) -> Optional[HubSessionEntry]:
        entry = self._sessions.pop(session_id, None)
        if entry:
            logger.info(f"[HUB_REGISTRY] Removed session {session_id}")
        return entry

    def cleanup_expired(self, ttl: float = 300.0) -> int:
        """Remove sessions idle for more than ttl seconds."""
        now = time.monotonic()
        expired = [
            sid for sid, entry in self._sessions.items()
            if now - entry.last_activity > ttl
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
        if expired:
            logger.info(f"[HUB_REGISTRY] Cleaned up {len(expired)} expired sessions")
        return len(expired)
