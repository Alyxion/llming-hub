"""News widget provider — wraps NewsAdapter with change detection."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Callable, Optional

from llming_hub.adapters.news import NewsAdapter
from llming_hub.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class NewsWidgetProvider(BaseProvider):
    widget_id = "news"
    interval = 300.0  # 5 minutes

    def __init__(
        self,
        adapter: NewsAdapter,
        locale: str = "en-us",
        image_url_rewriter: Callable[[str, str], str] | None = None,
        channels: list[str] | None = None,
    ):
        self.adapter = adapter
        self.locale = locale
        self._image_url_rewriter = image_url_rewriter
        self._channels = channels or ["All"]
        self._last_hash: str = ""

    async def fetch_data(self, params=None) -> Optional[dict[str, Any]]:
        try:
            articles = await self.adapter.get_articles(limit=20, locale=self.locale)
            payload = {
                "channels": self._channels,
                "articles": [
                    {
                        "id": a.id,
                        "title": a.title,
                        "teaser": a.teaser,
                        "image": self._rewrite_image(a.id, a.image),
                        "published": a.published_label or a.published_at,
                        "author": a.author_name,
                        "web_link": a.web_link,
                        "channel": a.channel,
                    }
                    for a in articles
                ]
            }

            h = hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if h == self._last_hash:
                return None
            self._last_hash = h
            return payload
        except Exception as e:
            logger.warning(f"[NEWS_PROVIDER] Error: {e}")
            return {"error": str(e)}

    def _rewrite_image(self, article_id: str, image_url: str) -> str:
        if self._image_url_rewriter and image_url:
            return self._image_url_rewriter(article_id, image_url)
        return image_url
