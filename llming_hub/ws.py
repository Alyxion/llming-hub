"""Hub WebSocket — FastAPI router + HubController."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from llming_hub.registry import HubSessionRegistry, HubSessionEntry
from llming_hub.providers.apps import ApplicationsProvider

logger = logging.getLogger(__name__)


class HubController:
    """Server-side controller for a single hub WebSocket session."""

    def __init__(self, entry: HubSessionEntry, session_id: str):
        self.entry = entry
        self.session_id = session_id
        self._providers: list = []
        self._provider_tasks: list[asyncio.Task] = []

    async def send(self, msg: dict):
        ws = self.entry.websocket
        if ws:
            try:
                await ws.send_json(msg)
            except Exception:
                pass

    async def handle_message(self, msg: dict):
        msg_type = msg.get("type", "")

        if msg_type == "heartbeat":
            return

        if msg_type == "request_data":
            widget_id = msg.get("widget_id", "")
            params = msg.get("params")
            await self._handle_request_data(widget_id, params=params)
            return

        logger.debug(f"[HUB_WS] Unknown message type: {msg_type}")

    async def _handle_request_data(self, widget_id: str, params: dict = None):
        for provider in self._providers:
            if provider.widget_id == widget_id:
                try:
                    data = await provider.fetch_data(params=params)
                    if data is not None:
                        await self.send({
                            "type": "widget_data",
                            "widget_id": widget_id,
                            "data": data,
                        })
                except Exception as e:
                    logger.warning(f"[HUB_WS] Error fetching {widget_id}: {e}")
                return

    def register_provider(self, provider):
        self._providers.append(provider)
        task = asyncio.create_task(self._run_provider(provider))
        self._provider_tasks.append(task)

    async def _run_provider(self, provider):
        try:
            data = await provider.fetch_data()
            if data is not None:
                await self.send({
                    "type": "widget_data",
                    "widget_id": provider.widget_id,
                    "data": data,
                })
            while True:
                await asyncio.sleep(provider.interval)
                try:
                    data = await provider.fetch_data()
                    if data is not None:
                        await self.send({
                            "type": "widget_data",
                            "widget_id": provider.widget_id,
                            "data": data,
                        })
                except Exception as e:
                    logger.warning(f"[HUB_WS] Provider {provider.widget_id} error: {e}")
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
    """Build the FastAPI router for hub WebSocket connections."""
    router = APIRouter()

    @router.websocket(f"{ws_prefix}/ws/{{session_id}}")
    async def hub_ws_endpoint(websocket: WebSocket, session_id: str):
        registry = HubSessionRegistry.get()
        entry = registry.get_session(session_id)
        if not entry:
            await websocket.close(code=4004, reason="Session not found")
            return

        await websocket.accept()
        entry.websocket = websocket
        controller = HubController(entry, session_id)
        entry.controller = controller

        try:
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

            # Message loop
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                    await controller.handle_message(msg)
                except json.JSONDecodeError:
                    logger.warning(f"[HUB_WS] Invalid JSON from {session_id}")

        except WebSocketDisconnect:
            logger.info(f"[HUB_WS] Client disconnected: {session_id}")
        except Exception as e:
            logger.exception(f"[HUB_WS] Error in session {session_id}: {e}")
        finally:
            await controller.cleanup()
            entry.websocket = None
            entry.controller = None

    return router
