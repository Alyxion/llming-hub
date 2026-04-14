"""Hub session registry — extends llming-com base classes."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from llming_com import BaseSessionEntry, BaseSessionRegistry

logger = logging.getLogger(__name__)


@dataclass
class HubSessionEntry(BaseSessionEntry):
    """Hub session entry with widget and locale metadata."""

    locale: str = "en-us"
    active_widgets: list[str] = field(default_factory=list)
    user_context: Any = None  # opaque app-specific user data (e.g. O365 user)
    config: dict = field(default_factory=dict)


class HubSessionRegistry(BaseSessionRegistry["HubSessionEntry"]):
    """Hub session registry — singleton with TTL cleanup.

    Extends BaseSessionRegistry with a convenience ``register_user`` method
    that builds a HubSessionEntry from keyword args (backward compat).
    """

    def register_user(
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
        """Register a hub session from user details (convenience method)."""
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
        return self.register(session_id, entry)
