"""Debug API for hub sessions.

Endpoints:
  GET  /api/hub/debug/sessions              — list all active hub sessions
  GET  /api/hub/debug/sessions/{id}         — session detail
  POST /api/hub/debug/sessions/{id}/refresh — trigger immediate data push
  GET  /api/hub/debug/sessions/{id}/fetch/{widget_id} — fetch widget data
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from llming_hub.registry import HubSessionRegistry

logger = logging.getLogger(__name__)


class RefreshRequest(BaseModel):
    widget_id: str


def build_hub_debug_router(
    auth_dependency: Optional[Callable] = None,
    prefix: str = "/api/hub/debug",
) -> APIRouter:
    """Build the hub debug API router."""

    deps = [Depends(auth_dependency)] if auth_dependency else []

    router = APIRouter(
        prefix=prefix,
        dependencies=deps,
    )

    @router.get("/sessions")
    async def list_sessions():
        registry = HubSessionRegistry.get()
        sessions = []
        now = time.monotonic()
        for sid, entry in registry._sessions.items():
            sessions.append({
                "session_id": sid,
                "user_id": entry.user_id,
                "user_name": entry.user_name,
                "user_email": entry.user_email,
                "ws_connected": entry.websocket is not None,
                "active_widgets": entry.active_widgets,
                "idle_seconds": round(now - entry.last_activity),
                "created_ago_seconds": round(now - entry.created_at),
            })
        return {"count": len(sessions), "sessions": sessions}

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        registry = HubSessionRegistry.get()
        entry = registry.get_session(session_id)
        if not entry:
            raise HTTPException(404, f"Session {session_id} not found")

        now = time.monotonic()
        return {
            "session_id": session_id,
            "user_id": entry.user_id,
            "user_name": entry.user_name,
            "user_email": entry.user_email,
            "user_avatar": entry.user_avatar,
            "locale": entry.locale,
            "ws_connected": entry.websocket is not None,
            "active_widgets": entry.active_widgets,
            "idle_seconds": round(now - entry.last_activity),
            "created_ago_seconds": round(now - entry.created_at),
            "config": entry.config,
            "has_user_context": entry.user_context is not None,
        }

    @router.post("/sessions/{session_id}/refresh")
    async def refresh_widget(session_id: str, body: RefreshRequest):
        registry = HubSessionRegistry.get()
        entry = registry.get_session(session_id)
        if not entry:
            raise HTTPException(404, f"Session {session_id} not found")
        if not entry.controller:
            raise HTTPException(409, "WebSocket not connected (no controller)")

        await entry.controller._handle_request_data(body.widget_id)
        return {"status": "refresh_sent", "widget_id": body.widget_id}

    @router.get("/sessions/{session_id}/fetch/{widget_id}")
    async def fetch_widget(session_id: str, widget_id: str):
        registry = HubSessionRegistry.get()
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

    return router
