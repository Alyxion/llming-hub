"""Hub landing page — NiceGUI page factory.

Creates the @ui.page route that injects JS/CSS and bootstraps the hub.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING
from uuid import uuid4

from nicegui import ui, app

if TYPE_CHECKING:
    from llming_hub.config import HubConfig

logger = logging.getLogger(__name__)


def create_hub_page(config: "HubConfig", route: str = "/"):
    """Register a NiceGUI page route for the hub landing page."""
    from llming_hub.registry import HubSessionRegistry

    @ui.page(route)
    async def hub_route():
        try:
            await _hub_route_impl(config)
        except Exception as e:
            logger.exception(f"[HUB] hub_route crashed: {e}")
            ui.label(f"Error: {e}").classes("text-red-500")


async def _hub_route_impl(config: "HubConfig"):
    from llming_hub.registry import HubSessionRegistry

    # Call the consuming app's session_setup callback
    if not config.session_setup:
        ui.label("Hub not configured: no session_setup callback").classes("text-red-500")
        return

    session_info = await config.session_setup()
    if session_info is None:
        return  # Auth failed or redirect happened

    user = session_info.user
    i18n = session_info.i18n

    # Register session
    session_id = str(uuid4())
    registry = HubSessionRegistry.get()
    registry.register(
        session_id=session_id,
        user_id=user.user_id,
        user_name=user.given_name or user.user_name,
        user_email=user.user_email,
        user_avatar=user.user_avatar,
        locale=user.locale,
        active_widgets=session_info.active_widgets,
        user_context=session_info.extra.get("user_context"),
        config={
            "greeting": session_info.greeting,
            "banner_html": session_info.banner_html,
            "apps": session_info.apps,
            "version": session_info.version,
            "copyright": session_info.copyright,
            "is_admin": session_info.is_admin,
            "dev_overrides": session_info.dev_overrides,
            "dev_overrides_label": session_info.dev_overrides_label,
            "i18n": i18n,
            **session_info.config_extra,
        },
    )

    # Cleanup on disconnect
    def _cleanup():
        registry.remove(session_id)
    ui.context.client.on_disconnect(_cleanup)

    # Build config payload for the client
    config_payload = {
        "sessionId": session_id,
        "wsPath": f"{config.ws_prefix}/ws/{session_id}",
        "userName": user.given_name or user.user_name,
        "fullName": user.user_name,
        "userEmail": user.user_email,
        "userAvatar": user.user_avatar,
        "isAdmin": session_info.is_admin,
        "greeting": session_info.greeting,
        "locale": user.locale,
        "bannerHtml": session_info.banner_html,
        "apps": session_info.apps,
        "activeWidgets": session_info.active_widgets,
        "version": session_info.version,
        "copyright": session_info.copyright,
        "devOverrides": session_info.dev_overrides,
        "devOverridesLabel": session_info.dev_overrides_label,
        "i18n": i18n,
        # Extra config from consuming app (e.g. weather_city_display)
        **session_info.config_extra,
        # Branding from HubConfig
        "branding": {
            "logoUrl": config.logo_url,
            "appTitle": config.app_title,
            "accentColor": config.accent_color,
            "bgDarkUrl": config.bg_dark_url,
            "bgLightUrl": config.bg_light_url,
            "mascotUrl": config.mascot_url,
            "adminUrl": session_info.admin_url,
            "settingsUrl": session_info.settings_url,
            "devOverridesUrl": session_info.dev_overrides_url,
        },
    }
    config_json = json.dumps(config_payload, ensure_ascii=False).replace("</", r"<\/")

    # Cache-bust suffix
    _cb = str(int(time.time()))
    sp = config.static_prefix

    _css_urls = [
        *session_info.extra_css_urls,
        f"{sp}/hub-core.css?v={_cb}",
    ]
    _js_scripts = [
        f"{sp}/hub-features.js?v={_cb}",     # must be first
        f"{sp}/hub-ws.js?v={_cb}",
        f"{sp}/hub-apps.js?v={_cb}",
        f"{sp}/hub-weather.js?v={_cb}",
        f"{sp}/hub-mail.js?v={_cb}",
        f"{sp}/hub-calendar.js?v={_cb}",
        f"{sp}/hub-news.js?v={_cb}",
        f"{sp}/hub-stats.js?v={_cb}",
        f"{sp}/hub-app-core.js?v={_cb}",     # must be last
    ]

    ui.run_javascript(f"""
        // -- CSS --
        {_css_urls!r}.forEach(href => {{
            if (!document.querySelector(`link[href="${{href}}"]`)) {{
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = href;
                document.head.appendChild(link);
            }}
        }});
        // -- hide NiceGUI content, mount hub --
        (function() {{
            const s = document.createElement('style');
            s.textContent = `
                .nicegui-content {{ padding: 0 !important; display: none !important; }}
                .q-page-container {{ height: 100vh; }}
                .q-page {{ height: 100%; }}
            `;
            document.head.appendChild(s);
        }})();
        if (!document.getElementById('hub-app')) {{
            const div = document.createElement('div');
            div.id = 'hub-app';
            div.style.cssText = 'position:fixed;inset:0;z-index:9999;';
            document.body.appendChild(div);
        }}
        // -- config + scripts --
        window.__HUB_CONFIG__ = {config_json};
        // -- preload avatar --
        if (window.__HUB_CONFIG__.userAvatar) {{
            const preload = document.createElement('link');
            preload.rel = 'preload';
            preload.as = 'image';
            preload.href = window.__HUB_CONFIG__.userAvatar;
            document.head.appendChild(preload);
        }}
        (async () => {{
            const loadScript = (src) => new Promise((resolve, reject) => {{
                const s = document.createElement('script');
                s.src = src;
                s.onload = resolve;
                s.onerror = reject;
                document.head.appendChild(s);
            }});
            await loadScript({_js_scripts[0]!r});
            await Promise.all({_js_scripts[1:-1]!r}.map(loadScript));
            await loadScript({_js_scripts[-1]!r});
        }})();
    """)
