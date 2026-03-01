"""Mail widget provider — wraps MailAdapter with change detection."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from llming_hub.adapters.mail import MailAdapter
from llming_hub.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class MailWidgetProvider(BaseProvider):
    widget_id = "mail"
    interval = 8.0

    def __init__(self, adapter: MailAdapter, user_email: str = ""):
        self.adapter = adapter
        self.user_email = user_email
        self._last_hash: str = ""

    async def fetch_data(self, params=None) -> Optional[dict[str, Any]]:
        try:
            inbox = await self.adapter.get_inbox(limit=20)

            now = datetime.now()
            total_inbox = inbox.total
            unread = sum(1 for email in inbox.emails if not email.is_read)

            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            new_today = 0
            for email in inbox.emails:
                if email.timestamp:
                    try:
                        ts = datetime.fromisoformat(email.timestamp)
                        if ts.replace(tzinfo=None) >= today:
                            new_today += 1
                    except ValueError:
                        pass

            messages = []
            for email in inbox.emails[:20]:
                ts_label = ""
                if email.timestamp:
                    try:
                        ts = datetime.fromisoformat(email.timestamp)
                        ts_naive = ts.replace(tzinfo=None)
                        diff = now - ts_naive
                        if diff < timedelta(minutes=1):
                            ts_label = "just now"
                        elif diff < timedelta(hours=1):
                            ts_label = f"{int(diff.total_seconds() / 60)}m"
                        elif diff < timedelta(days=1):
                            ts_label = f"{int(diff.total_seconds() / 3600)}h"
                        elif diff.days == 1:
                            ts_label = "yesterday"
                        elif diff.days < 7:
                            ts_label = f"{diff.days}d"
                        else:
                            ts_label = ts_naive.strftime("%d.%m.")
                    except ValueError:
                        ts_label = email.timestamp

                preview = (email.body_preview or "")[:120]

                messages.append({
                    "from_name": email.from_name or "",
                    "from_email": email.from_email or "",
                    "subject": email.subject or "",
                    "body_preview": preview,
                    "timestamp": ts_label,
                    "is_read": email.is_read,
                    "importance": email.importance or "normal",
                    "has_attachments": email.has_attachments,
                    "web_link": email.web_link or "",
                })

            payload = {
                "mailbox": self.user_email,
                "total": total_inbox,
                "unread": unread,
                "new_today": new_today,
                "messages": messages,
            }

            h = hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if h == self._last_hash:
                return None
            self._last_hash = h
            return payload
        except Exception as e:
            logger.warning(f"[MAIL_PROVIDER] Error: {e}")
            return {"error": str(e), "mailbox": self.user_email}
