"""Stats widget provider — wraps StatsAdapter."""

from __future__ import annotations

import logging
from typing import Any, Optional

from llming_hub.adapters.stats import StatsAdapter
from llming_hub.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class StatsWidgetProvider(BaseProvider):
    widget_id = "stats"
    interval = 30.0

    def __init__(self, adapter: StatsAdapter):
        self.adapter = adapter

    async def fetch_data(self, params=None) -> Optional[dict[str, Any]]:
        try:
            rows = await self.adapter.get_stats()
            return {
                "rows": [
                    {"label": r.label, "icon": r.icon, "color": r.color, "today": r.today, "week": r.week}
                    for r in rows
                ]
            }
        except Exception as e:
            logger.warning(f"[STATS_PROVIDER] Error: {e}")
            return {"error": str(e)}
