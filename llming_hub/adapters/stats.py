"""Stats adapter — abstract interface for fetching statistics data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StatsRow:
    """A single statistics row."""
    label: str
    icon: str
    color: str
    today: int | float
    week: int | float


class StatsAdapter(ABC):
    """Abstract interface for fetching statistics data."""

    @abstractmethod
    async def get_stats(self) -> list[StatsRow]:
        """Fetch current statistics rows."""
        ...
