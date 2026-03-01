"""Directory adapter — unified identity + avatar service."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DirectoryUser:
    """A user from the company directory."""
    id: str
    display_name: str
    email: str
    given_name: str = ""
    surname: str = ""
    job_title: str = ""
    department: str = ""


class DirectoryAdapter(ABC):
    """Abstract interface for resolving users and avatar URLs."""

    @abstractmethod
    async def get_user_by_email(self, email: str) -> DirectoryUser | None:
        """Look up a user by email address."""
        ...

    @abstractmethod
    async def get_avatar_url(self, user_id: str, width: int = 64, height: int = 64) -> str:
        """Return the URL for a user's avatar image."""
        ...
