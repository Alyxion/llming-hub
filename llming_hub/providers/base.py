"""Base provider for hub widget data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseProvider(ABC):
    """Abstract base for hub data providers.

    Subclasses implement fetch_data() which returns a dict payload
    pushed to the client as { type: "widget_data", widget_id, data }.
    """

    widget_id: str = ""
    interval: float = 60.0  # seconds between pushes

    @abstractmethod
    async def fetch_data(self, params: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        """Fetch and return widget data, or None to skip this push.

        Args:
            params: Optional parameters from client request (e.g. city override).
        """
        ...
