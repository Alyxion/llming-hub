"""LandingHub — main orchestrator for the hub landing page.

No NiceGUI dependency — uses FastAPI/Starlette for routing and static files.
"""

from __future__ import annotations

import logging
from pathlib import Path

from llming_hub.config import HubConfig

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"


class LandingHub:
    """Main entry point — consuming app creates one and calls mount()."""

    def __init__(self, config: HubConfig):
        self.config = config

    def mount(self, fastapi_app, route: str = "/"):
        """Register static files, WS router, debug API, data API, and page route."""
        from starlette.staticfiles import StaticFiles
        from llming_hub.ws import build_hub_router
        from llming_hub.page import create_hub_page

        # 1. Static files
        fastapi_app.mount(
            self.config.static_prefix,
            StaticFiles(directory=str(_STATIC_DIR)),
            name="llming-hub-static",
        )

        # 2. WS router
        fastapi_app.include_router(
            build_hub_router(
                provider_factory=self.config.provider_factory,
                ws_prefix=self.config.ws_prefix,
            )
        )

        # 3. Debug API (optional)
        if self.config.debug_auth_dependency:
            from llming_hub.debug_api import build_hub_debug_router
            fastapi_app.include_router(
                build_hub_debug_router(
                    auth_dependency=self.config.debug_auth_dependency,
                )
            )

        # 4. Data endpoint (optional — photo/thumbnail handlers)
        if self.config.data_handlers:
            from llming_hub.data_api import build_hub_data_router
            fastapi_app.include_router(
                build_hub_data_router(
                    handlers=self.config.data_handlers,
                    prefix=self.config.data_prefix,
                )
            )

        # 5. Hub page route (pure HTML — no NiceGUI)
        # Must use routes.insert(0, ...) to beat NiceGUI's ASGI middleware
        # which intercepts all routes before FastAPI's router processes them.
        # Same pattern as llming-lodge's chat page registration.
        from starlette.routing import Route
        fastapi_app.routes.insert(0, Route(
            route, create_hub_page(self.config, route=route), methods=["GET"],
        ))

        logger.info("[LLMING_HUB] Mounted at route=%s, static=%s", route, self.config.static_prefix)
