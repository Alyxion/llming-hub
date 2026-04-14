"""Hub WebSocket — FastAPI router + HubController.

Uses llming-com's transport layer for the WS lifecycle and BaseController
for rate limiting.  Hub-specific logic (providers, widgets) is layered on top.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Callable

from fastapi import APIRouter, WebSocket

from llming_com import BaseController, run_websocket_session

from llming_hub.registry import HubSessionRegistry, HubSessionEntry
from llming_hub.providers.apps import ApplicationsProvider

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 30  # seconds — max time for a single provider fetch
_MAX_WS_MESSAGE_SIZE = 8192  # bytes — max WebSocket message size


class HubController(BaseController):
    """Server-side controller for a single hub WebSocket session.

    Extends BaseController with provider management and widget data push.
    """

    def __init__(self, entry: HubSessionEntry, session_id: str):
        super().__init__(session_id, rate_limit_window=60.0, rate_limit_max=30)
        self.entry = entry
        self._providers: list = []
        self._provider_tasks: list[asyncio.Task] = []

    async def send(self, msg: dict) -> bool:
        """Send via the entry's websocket (hub pattern)."""
        ws = self.entry.websocket
        if ws:
            try:
                await ws.send_json(msg)
                return True
            except Exception:
                return False
        return False

    async def handle_message(self, msg: dict) -> None:
        """Handle an incoming WebSocket message."""
        msg_type = msg.get("type", "")

        if msg_type == "heartbeat":
            return

        if msg_type == "request_data":
            if not self.check_rate_limit():
                logger.warning("[HUB_WS] Rate limit exceeded for %s…", self.session_id[:8])
                return
            widget_id = msg.get("widget_id", "")
            params = msg.get("params")
            if params is not None and not isinstance(params, dict):
                logger.warning("[HUB_WS] Invalid params type from %s…: %s",
                               self.session_id[:8], type(params).__name__)
                return
            await self._handle_request_data(widget_id, params=params)
            return

        logger.debug("[HUB_WS] Unknown message type: %s", msg_type)

    async def _handle_request_data(self, widget_id: str, params: dict = None):
        for provider in self._providers:
            if provider.widget_id == widget_id:
                try:
                    data = await asyncio.wait_for(
                        provider.fetch_data(params=params), timeout=_FETCH_TIMEOUT,
                    )
                    if data is not None:
                        await self.send({
                            "type": "widget_data",
                            "widget_id": widget_id,
                            "data": data,
                        })
                except asyncio.TimeoutError:
                    logger.warning("[HUB_WS] On-demand fetch %s timed out", widget_id)
                except Exception as e:
                    logger.warning("[HUB_WS] Error fetching %s: %s", widget_id, e)
                return

    def register_provider(self, provider):
        self._providers.append(provider)
        task = asyncio.create_task(self._run_provider(provider))
        self._provider_tasks.append(task)

    async def _fetch_with_timeout(self, provider):
        return await asyncio.wait_for(provider.fetch_data(), timeout=_FETCH_TIMEOUT)

    async def _run_provider(self, provider):
        try:
            data = await self._fetch_with_timeout(provider)
            if data is not None:
                await self.send({
                    "type": "widget_data",
                    "widget_id": provider.widget_id,
                    "data": data,
                })
            while True:
                await asyncio.sleep(provider.interval)
                try:
                    data = await self._fetch_with_timeout(provider)
                    if data is not None:
                        await self.send({
                            "type": "widget_data",
                            "widget_id": provider.widget_id,
                            "data": data,
                        })
                except asyncio.TimeoutError:
                    logger.warning("[HUB_WS] Provider %s timed out after %ds",
                                   provider.widget_id, _FETCH_TIMEOUT)
                except Exception as e:
                    logger.warning("[HUB_WS] Provider %s error: %s", provider.widget_id, e)
        except asyncio.TimeoutError:
            logger.warning("[HUB_WS] Provider %s initial fetch timed out", provider.widget_id)
        except asyncio.CancelledError:
            pass

    async def cleanup(self):
        for task in self._provider_tasks:
            task.cancel()
        if self._provider_tasks:
            await asyncio.gather(*self._provider_tasks, return_exceptions=True)
        self._provider_tasks.clear()
        self._providers.clear()


def build_hub_router(
    provider_factory: Optional[Callable] = None,
    ws_prefix: str = "/api/hub",
) -> APIRouter:
    """Build the FastAPI router for hub WebSocket connections.

    Uses llming-com's ``run_websocket_session`` for the WS lifecycle.
    """
    router = APIRouter()

    @router.websocket(f"{ws_prefix}/ws/{{session_id}}")
    async def hub_ws_endpoint(websocket: WebSocket, session_id: str):
        registry = HubSessionRegistry.get()

        async def on_connect(entry: HubSessionEntry, ws: WebSocket):
            controller = HubController(entry, session_id)
            entry.controller = controller

            await controller.send({
                "type": "hub_init",
                "user_name": entry.user_name,
                "user_email": entry.user_email,
                "user_avatar": entry.user_avatar,
                "locale": entry.locale,
                "active_widgets": entry.active_widgets,
                "config": entry.config,
            })

            # Start providers
            controller.register_provider(ApplicationsProvider())
            if provider_factory:
                for widget_id in entry.active_widgets:
                    provider = provider_factory(widget_id, entry)
                    if provider:
                        controller.register_provider(provider)

        async def on_message(entry: HubSessionEntry, msg: dict):
            if entry.controller:
                await entry.controller.handle_message(msg)

        async def on_disconnect(sid: str, entry: HubSessionEntry):
            if entry.controller:
                await entry.controller.cleanup()
                entry.controller = None

        await run_websocket_session(
            websocket, session_id, registry,
            on_connect=on_connect,
            on_message=on_message,
            on_disconnect=on_disconnect,
            max_message_size=_MAX_WS_MESSAGE_SIZE,
            log_prefix="HUB_WS",
        )

    return router
