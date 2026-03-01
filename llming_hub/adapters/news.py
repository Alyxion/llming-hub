"""News adapter — abstract interface for fetching news articles."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NewsArticle:
    """A single news article."""
    id: str
    title: str
    teaser: str
    image: str = ""
    published_at: str = ""
    published_label: str = ""
    author_name: str = ""
    web_link: str = ""
    channel: str = ""  # e.g. "Metzingen" — empty string = global


class NewsAdapter(ABC):
    """Abstract interface for fetching news articles."""

    @abstractmethod
    async def get_articles(self, limit: int = 8, locale: str = "en-us") -> list[NewsArticle]:
        """Fetch recent news articles."""
        ...
