"""Calendar adapter — abstract interface for fetching calendar events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CalAttendee:
    """A calendar event attendee."""
    name: str
    email: str


@dataclass
class CalEvent:
    """A calendar event."""
    id: str
    subject: str
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False
    location: str = ""
    is_online_meeting: bool = False
    online_meeting_url: str = ""
    sensitivity: str = "normal"
    show_as: str = "busy"
    importance: str = "normal"
    attendees: list[CalAttendee] = field(default_factory=list)


class CalendarAdapter(ABC):
    """Abstract interface for fetching calendar events."""

    @abstractmethod
    async def get_events(self, start: datetime, end: datetime, limit: int = 20) -> list[CalEvent]:
        """Fetch calendar events within the given time range."""
        ...
