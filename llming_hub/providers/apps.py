"""Applications provider — no-op placeholder (apps are static in config)."""

from __future__ import annotations

from typing import Any, Optional
from llming_hub.providers.base import BaseProvider


class ApplicationsProvider(BaseProvider):
    widget_id = "applications"
    interval = 3600.0

    async def fetch_data(self, params=None) -> Optional[dict[str, Any]]:
        return None
