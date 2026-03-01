"""Weather adapter — abstract interface for fetching weather data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class WeatherHourForecast:
    """A single hourly forecast entry."""
    time: str
    icon: str
    temp: int


@dataclass
class WeatherDayForecast:
    """A day-level forecast summary."""
    label: str
    min_temp: int
    max_temp: int
    condition: str
    icon: str = ""


@dataclass
class WeatherData:
    """Complete weather data for a location."""
    city: str
    temp: int
    condition: str
    condition_icon: str
    humidity: int
    wind_speed: int
    wind_deg: int
    upcoming: list[WeatherHourForecast] = field(default_factory=list)
    today: WeatherDayForecast | None = None
    tomorrow: WeatherDayForecast | None = None
    forecast: list[WeatherDayForecast] = field(default_factory=list)
    city_id: str | int = ""
    timezone_offset: int = 0  # seconds from UTC


class WeatherAdapter(ABC):
    """Abstract interface for fetching weather data."""

    @abstractmethod
    async def get_weather(self, city: str | None = None, city_display: str | None = None) -> WeatherData:
        """Fetch current weather + forecast data.

        Args:
            city: Optional city query override (e.g. "Thane,IN").
            city_display: Optional display name override (e.g. "Thane").
        """
        ...
