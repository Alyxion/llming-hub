"""Calendar widget provider — wraps CalendarAdapter with avatar resolution."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import quote

from llming_hub.adapters.calendar import CalendarAdapter, CalEvent
from llming_hub.adapters.directory import DirectoryAdapter
from llming_hub.providers.base import BaseProvider

logger = logging.getLogger(__name__)


def _get_initials(name: str) -> str:
    """Extract up to 2 initials from a display name."""
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "?"


_WEEKDAY_SHORT: dict[str, list[str]] = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    "fr": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
    "it": ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"],
    "hi": ["\u0938\u094b\u092e", "\u092e\u0902\u0917\u0932", "\u092c\u0941\u0927", "\u0917\u0941\u0930\u0941", "\u0936\u0941\u0915\u094d\u0930", "\u0936\u0928\u093f", "\u0930\u0935\u093f"],
}


class CalendarWidgetProvider(BaseProvider):
    widget_id = "calendar"
    interval = 120.0

    def __init__(
        self,
        adapter: CalendarAdapter,
        directory: DirectoryAdapter | None = None,
        event_web_link_template: str = "",
        locale: str = "en",
        tomorrow_label: str = "Tomorrow",
    ):
        self.adapter = adapter
        self.directory = directory
        self.event_web_link_template = event_web_link_template
        self._locale = locale[:2].lower()
        self._tomorrow_label = tomorrow_label
        self._last_hash: str = ""

    async def fetch_data(self, params=None) -> Optional[dict[str, Any]]:
        try:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            raw_events = await self.adapter.get_events(
                start=today_start,
                end=today_start + timedelta(days=60),
                limit=20,
            )

            events = []
            has_unresolved = False
            idx = 0
            for ev in raw_events:
                if not ev.is_all_day and ev.end_time.replace(tzinfo=None) < now:
                    continue
                formatted = await self._format_event(ev, now)
                formatted["_idx"] = idx
                if ev.attendees and not formatted.get("attendees"):
                    has_unresolved = True
                events.append(formatted)
                idx += 1
                if len(events) >= 20:
                    break

            payload = {"events": events}

            h = hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if h == self._last_hash:
                return None
            self._last_hash = h

            if has_unresolved:
                # Directory not ready — clear hash so next fetch re-sends
                # with resolved data, and use fast retry interval.
                self._last_hash = ""
                self.interval = 8.0
            else:
                self.interval = 120.0

            return payload
        except Exception as e:
            logger.warning(f"[CALENDAR_PROVIDER] Error: {e}")
            return {"error": str(e)}

    async def _format_event(self, ev: CalEvent, now: datetime) -> dict[str, Any]:
        today = now.date()
        ev_date = ev.start_time.date()

        if ev_date == today:
            date_label = ""
        elif ev_date == today + timedelta(days=1):
            date_label = self._tomorrow_label
        else:
            weekdays = _WEEKDAY_SHORT.get(self._locale, _WEEKDAY_SHORT["en"])
            wd = weekdays[ev.start_time.weekday()]
            date_label = f"{wd}, {ev.start_time.strftime('%d.%m.')}"

        if ev.is_all_day:
            time_str = ""
        else:
            time_str = f"{ev.start_time.strftime('%H:%M')}\u2013{ev.end_time.strftime('%H:%M')}"

        # Resolve attendee avatars via directory adapter
        attendees = []
        if self.directory:
            for att in ev.attendees[:5]:
                if not att.email:
                    continue
                user = await self.directory.get_user_by_email(att.email)
                if user:
                    avatar = await self.directory.get_avatar_url(user.id, width=32, height=32)
                    initials = _get_initials(user.display_name or att.name or "")
                    attendees.append({
                        "name": user.display_name or att.name or "",
                        "avatar": avatar,
                        "initials": initials,
                    })

        is_private = ev.sensitivity in ("private", "confidential")
        is_teams = bool(ev.is_online_meeting) or bool(ev.location and "teams" in ev.location.lower())

        web_link = ""
        if self.event_web_link_template and ev.id:
            web_link = self.event_web_link_template.format(event_id=quote(ev.id, safe=""))

        return {
            "subject": ev.subject or "",
            "date_label": date_label,
            "time_str": time_str,
            "location": ev.location or "",
            "is_all_day": ev.is_all_day,
            "is_private": is_private,
            "is_teams": is_teams,
            "is_online_meeting": ev.is_online_meeting,
            "online_meeting_url": ev.online_meeting_url or "",
            "show_as": ev.show_as or "busy",
            "importance": ev.importance or "normal",
            "attendees": attendees,
            "web_link": web_link,
        }
