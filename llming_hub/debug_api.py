"""Debug API for hub sessions — extends llming-com's base debug router.

Endpoints:
  GET  /api/hub/debug/sessions              — list all active hub sessions
  GET  /api/hub/debug/sessions/{id}         — session detail
  POST /api/hub/debug/sessions/{id}/ws_send — forward WS message
  POST /api/hub/debug/sessions/{id}/refresh — trigger immediate data push
  GET  /api/hub/debug/sessions/{id}/fetch/{widget_id} — fetch widget data
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from llming_com import build_debug_router

from llming_hub.registry import HubSessionRegistry, HubSessionEntry

logger = logging.getLogger(__name__)


class RefreshRequest(BaseModel):
    widget_id: str


def _session_detail(session_id: str, entry: HubSessionEntry) -> dict:
    """Hub-specific session detail fields."""
    return {
        "locale": entry.locale,
        "active_widgets": entry.active_widgets,
        "config": entry.config,
        "has_user_context": entry.user_context is not None,
    }


def _add_hub_routes(router: APIRouter, registry: HubSessionRegistry) -> None:
    """Register hub-specific debug endpoints (refresh, fetch)."""

    @router.post("/sessions/{session_id}/refresh")
    async def refresh_widget(session_id: str, body: RefreshRequest):
        entry = registry.get_session(session_id)
        if not entry:
            raise HTTPException(404, f"Session {session_id} not found")
        if not entry.controller:
            raise HTTPException(409, "WebSocket not connected (no controller)")
        await entry.controller._handle_request_data(body.widget_id)
        return {"status": "refresh_sent", "widget_id": body.widget_id}

    @router.get("/sessions/{session_id}/fetch/{widget_id}")
    async def fetch_widget(session_id: str, widget_id: str):
        entry = registry.get_session(session_id)
        if not entry:
            raise HTTPException(404, f"Session {session_id} not found")
        if not entry.controller:
            raise HTTPException(409, "WebSocket not connected (no controller)")
        for provider in entry.controller._providers:
            if provider.widget_id == widget_id:
                data = await provider.fetch_data()
                return {"widget_id": widget_id, "data": data}
        raise HTTPException(404, f"Provider '{widget_id}' not found")


def build_hub_debug_router(
    auth_dependency: Optional[Callable] = None,
    prefix: str = "/api/hub/debug",
) -> APIRouter:
    """Build the hub debug API router using llming-com's base."""
    registry = HubSessionRegistry.get()
    return build_debug_router(
        registry,
        api_key_env="HUB_DEBUG_API_KEY",
        prefix=prefix,
        session_detail_hook=_session_detail,
        extra_routes=lambda r, reg: _add_hub_routes(r, reg),
    )
