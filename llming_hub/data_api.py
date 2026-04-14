"""Hub data endpoint — generic HTTP endpoint system for plugin resources.

Provides HubDataHandler (ABC for plugin handlers), ResourceCache (async-safe
process-global cache with per-key locking), and build_hub_data_router() to
mount the catch-all GET endpoint.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from fastapi import APIRouter, Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HubDataHandler ABC
# ---------------------------------------------------------------------------

class HubDataHandler(ABC):
    """Base class for hub data endpoint handlers.

    Consuming apps subclass this to serve plugin-specific resources
    (photos, thumbnails, etc.) through the generic hub data endpoint.
    """

    plugin_id: str = ""
    cache_ttl: float | None = 3600.0  # seconds; None = forever, 0 = no caching
    cache_max_entries: int = 500
    http_cache_control: str = "private, max-age=3600"

    @abstractmethod
    async def handle(self, resource_path: str, request: Request) -> tuple[bytes | None, str, int]:
        """Fetch the resource and return (bytes, media_type, status_code).

        Return (None, "", 404) for not-found resources.
        """
        ...

    def cache_key(self, resource_path: str, request: Request) -> str:
        """Build cache key.  Override for size variants, etc."""
        return f"{self.plugin_id}:{resource_path}"


# ---------------------------------------------------------------------------
# ResourceCache
# ---------------------------------------------------------------------------

@dataclass
class _CacheEntry:
    data: bytes | None
    media_type: str
    status_code: int
    created_at: float


class ResourceCache:
    """Process-global, asyncio-safe resource cache with per-key locking.

    Per-key locks prevent thundering-herd (e.g. 8 calendar attendee requests
    for the same user result in 1 upstream call).  LRU eviction is scoped
    by plugin prefix so one plugin's flood can't evict another's entries.
    """

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_lock(self, key: str) -> asyncio.Lock:
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def get_or_fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[tuple[bytes | None, str, int]]],
        ttl: float | None,
        max_entries: int,
    ) -> tuple[bytes | None, str, int]:
        """Return cached entry or call *fetcher* under per-key lock."""
        # Fast path — cache hit (no lock needed)
        entry = self._store.get(key)
        if entry is not None:
            if ttl is None or ttl == 0 or (time.time() - entry.created_at < ttl):
                return entry.data, entry.media_type, entry.status_code

        # Slow path — acquire per-key lock, re-check, fetch
        lock = await self._get_lock(key)
        async with lock:
            entry = self._store.get(key)
            if entry is not None:
                if ttl is None or ttl == 0 or (time.time() - entry.created_at < ttl):
                    return entry.data, entry.media_type, entry.status_code

            data, media_type, status_code = await fetcher()

            # Only cache successful (200) responses — errors and
            # temporary fallbacks (e.g. initials avatars) are not cached
            # so they can be replaced by real data on the next request.
            if ttl != 0 and status_code == 200:
                # Evict oldest entries for this plugin prefix if over limit
                prefix = key.split(":")[0] + ":"
                plugin_keys = sorted(
                    (k for k in self._store if k.startswith(prefix)),
                    key=lambda k: self._store[k].created_at,
                )
                while len(plugin_keys) >= max_entries:
                    evict_key = plugin_keys.pop(0)
                    self._store.pop(evict_key, None)
                    self._locks.pop(evict_key, None)

                # Periodically prune orphaned locks (every ~100 cache writes)
                if len(self._locks) > len(self._store) + 100:
                    self.cleanup_orphaned_locks()

                self._store[key] = _CacheEntry(
                    data=data,
                    media_type=media_type,
                    status_code=status_code,
                    created_at=time.time(),
                )

            return data, media_type, status_code

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)
        self._locks.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            self._store.pop(k, None)
            self._locks.pop(k, None)
        return len(keys)

    def cleanup_orphaned_locks(self) -> int:
        """Remove locks that have no corresponding cache entry."""
        orphaned = [k for k in self._locks if k not in self._store]
        for k in orphaned:
            self._locks.pop(k, None)
        return len(orphaned)


# Process-global singleton
_cache = ResourceCache()


def get_resource_cache() -> ResourceCache:
    return _cache


# ---------------------------------------------------------------------------
# Router builder
# ---------------------------------------------------------------------------

def build_hub_data_router(
    handlers: dict[str, HubDataHandler],
    prefix: str = "/api/hub/data",
) -> APIRouter:
    """Build a FastAPI router with a catch-all GET for hub data resources."""
    router = APIRouter()
    cache = get_resource_cache()

    @router.get(prefix + "/{plugin_id}/{resource_path:path}")
    async def hub_data_endpoint(plugin_id: str, resource_path: str, request: Request):
        # 0. Path traversal guard
        from pathlib import PurePosixPath
        resolved = PurePosixPath(resource_path)
        if resolved.is_absolute() or ".." in resolved.parts:
            return Response(status_code=400, content="Invalid resource path")

        # 1. Auth — require valid NiceGUI session cookie
        if not request.session.get("id"):
            return Response(status_code=401, content="Not authenticated")

        # 2. Look up handler
        handler = handlers.get(plugin_id)
        if not handler:
            return Response(status_code=404, content="Unknown plugin")

        # 3. Cache lookup / fetch
        key = handler.cache_key(resource_path, request)

        async def _fetch():
            return await handler.handle(resource_path, request)

        data, media_type, status_code = await cache.get_or_fetch(
            key=key,
            fetcher=_fetch,
            ttl=handler.cache_ttl,
            max_entries=handler.cache_max_entries,
        )

        # 4. Return response
        if data is None or status_code >= 400:
            return Response(status_code=status_code or 404, content="Not found")

        # For cached (200) responses use handler's cache header;
        # for temporary/fallback (2xx non-200) tell browser not to cache.
        cache_hdr = handler.http_cache_control if status_code == 200 else "no-store"
        return Response(
            content=data,
            media_type=media_type,
            headers={"Cache-Control": cache_hdr},
        )

    return router
