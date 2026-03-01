"""Weather widget provider — wraps WeatherAdapter."""

from __future__ import annotations

import logging
from typing import Any, Optional

from llming_hub.adapters.weather import WeatherAdapter
from llming_hub.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class WeatherWidgetProvider(BaseProvider):
    widget_id = "weather"
    interval = 600.0  # 10 minutes

    def __init__(self, adapter: WeatherAdapter):
        self.adapter = adapter
        self._last_city: str | None = None
        self._last_city_display: str | None = None

    async def fetch_data(self, params: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        try:
            # Remember last requested city for periodic refreshes
            if params and params.get("city"):
                self._last_city = params["city"]
                self._last_city_display = params.get("city_display")
            city = self._last_city
            city_display = self._last_city_display
            data = await self.adapter.get_weather(city=city, city_display=city_display)

            upcoming_data = [
                {"time": h.time, "icon": h.icon, "temp": h.temp}
                for h in data.upcoming
            ]

            forecast_data = [
                {
                    "label": f.label,
                    "min": f.min_temp,
                    "max": f.max_temp,
                    "condition": f.condition,
                    "icon": f.icon,
                }
                for f in data.forecast
            ]

            return {
                "city": data.city,
                "city_id": data.city_id,
                "temp": data.temp,
                "condition": data.condition,
                "condition_icon": data.condition_icon,
                "humidity": data.humidity,
                "wind_speed": data.wind_speed,
                "wind_deg": data.wind_deg,
                "upcoming": upcoming_data,
                "forecast": forecast_data,
                "timezone_offset": data.timezone_offset,
            }
        except Exception as e:
            logger.warning(f"[WEATHER_PROVIDER] Error: {e}")
            return {"city": "", "error": str(e)}
