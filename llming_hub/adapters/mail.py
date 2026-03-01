"""Mail adapter — abstract interface for fetching email data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MailMessage:
    """A single email message."""
    from_name: str
    from_email: str
    subject: str
    body_preview: str
    timestamp: str  # ISO 8601
    is_read: bool
    importance: str = "normal"
    has_attachments: bool = False
    web_link: str = ""


@dataclass
class MailInbox:
    """Summary of a user's inbox."""
    total: int
    emails: list[MailMessage] = field(default_factory=list)


class MailAdapter(ABC):
    """Abstract interface for fetching email data."""

    @abstractmethod
    async def get_inbox(self, limit: int = 10) -> MailInbox:
        """Fetch the user's inbox summary with recent messages."""
        ...
