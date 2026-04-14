"""Hub landing page — pure FastAPI/Starlette route.

Generates a static HTML page that bootstraps the hub SPA.
No NiceGUI dependency.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import HTMLResponse

if TYPE_CHECKING:
    from llming_hub.config import HubConfig

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"

# ── Content-hash cache busting ───────────────────────────────────
_file_hashes: dict[str, str] = {}


def _compute_file_hashes(static_dir: Path) -> dict[str, str]:
    """Compute MD5 content hashes for static files."""
    hashes = {}
    for fpath in static_dir.iterdir():
        if fpath.suffix in ('.js', '.css'):
            hashes[fpath.name] = hashlib.md5(fpath.read_bytes()).hexdigest()[:10]
    return hashes


def _hashed_url(prefix: str, filename: str) -> str:
    """Return URL with content hash for cache busting."""
    global _file_hashes
    if not _file_hashes:
        _file_hashes = _compute_file_hashes(_STATIC_DIR)
    h = _file_hashes.get(filename, "dev")
    return f"{prefix}/{filename}?v={h}"


def invalidate_hub_hashes() -> None:
    """Clear hash cache (called by dev file watcher)."""
    global _file_hashes
    _file_hashes = {}


# ── HTML builder ─────────────────────────────────────────────────

def _build_hub_html(config_json: str, css_urls: list[str], js_scripts: list[str],
                    extra_head: str = "", title: str = "Hub") -> str:
    """Build the complete HTML page for the hub SPA."""
    css_tags = "\n".join(f'<link rel="stylesheet" href="{url}">' for url in css_urls)
    # Phase 1: features.js first, Phase 2: widgets in parallel, Phase 3: core last
    js_phase1 = js_scripts[0] if js_scripts else ""
    js_phase2 = js_scripts[1:-1] if len(js_scripts) > 2 else []
    js_phase3 = js_scripts[-1] if len(js_scripts) > 1 else ""

    phase2_json = json.dumps(js_phase2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
{css_tags}
{extra_head}
</head>
<body>
<div id="hub-app" style="position:fixed;inset:0;"></div>
<script>window.__HUB_CONFIG__ = {config_json};</script>
<script>
// Preload avatar
if (window.__HUB_CONFIG__.userAvatar) {{
  const pl = document.createElement('link');
  pl.rel = 'preload'; pl.as = 'image';
  pl.href = window.__HUB_CONFIG__.userAvatar;
  document.head.appendChild(pl);
}}
// Load scripts in phases
(async () => {{
  const loadScript = src => new Promise((resolve, reject) => {{
    const s = document.createElement('script');
    s.src = src; s.onload = resolve;
    s.onerror = () => {{ s.remove(); setTimeout(() => {{
      const r = document.createElement('script');
      r.src = src; r.onload = resolve; r.onerror = reject;
      document.head.appendChild(r);
    }}, 500); }};
    document.head.appendChild(s);
  }});
  await loadScript({json.dumps(js_phase1)});
  await Promise.all({phase2_json}.map(loadScript));
  if ({json.dumps(js_phase3)}) await loadScript({json.dumps(js_phase3)});
}})();
</script>
</body>
</html>"""


# ── Route factory ────────────────────────────────────────────────

def create_hub_page(config: "HubConfig", route: str = "/"):
    """Create a FastAPI route handler for the hub page.

    Returns the async route function (to be registered by hub.mount).
    """
    from llming_hub.registry import HubSessionRegistry

    async def hub_route(request: Request) -> HTMLResponse:
        try:
            return await _hub_route_impl(config, request)
        except Exception as e:
            logger.exception("[HUB] hub_route crashed: %s", e)
            import html
            return HTMLResponse(
                f"<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>",
                status_code=500,
            )

    return hub_route


async def _hub_route_impl(config: "HubConfig", request: Request):
    from llming_hub.registry import HubSessionRegistry

    # ── OAuth callback interception ─────────────────────────
    # If this is a redirect back from the OAuth provider (?code=...),
    # delegate to the OAuth callback handler before doing anything else.
    if config.oauth_callback_handler and request.query_params.get("code"):
        return await config.oauth_callback_handler(request)

    if not config.session_setup:
        return HTMLResponse("<h1>Hub not configured</h1>", status_code=500)

    # Call the consuming app's session_setup callback.
    # Pass the request so the callback can check auth cookies.
    import inspect
    sig = inspect.signature(config.session_setup)
    if len(sig.parameters) > 0:
        session_info = await config.session_setup(request)
    else:
        session_info = await config.session_setup()

    if session_info is None:
        # Auth failed — clear stale cookies and initiate OAuth.
        # The session_setup callback returns None when the identity cookie
        # is missing, invalid, or expired (e.g. old secret, old format).
        from starlette.responses import RedirectResponse
        if config.oauth_start_handler:
            return await config.oauth_start_handler(request)
        # Fallback: clear cookies and redirect to self — the page will
        # show without user-specific data (no redirect loop since cookies
        # are cleared).
        response = RedirectResponse("/", status_code=302)
        response.delete_cookie("llming_identity", path="/")
        response.delete_cookie("llming_auth", path="/")
        response.delete_cookie("llming_session", path="/")
        return response

    user = session_info.user
    i18n = session_info.i18n

    # Register session
    session_id = str(uuid4())
    registry = HubSessionRegistry.get()
    registry.register_user(
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
            "permissions": session_info.permissions,
            "dev_overrides": session_info.dev_overrides,
            "dev_overrides_label": session_info.dev_overrides_label,
            "i18n": i18n,
            **session_info.config_extra,
        },
    )

    # Build config payload for the client
    config_payload = {
        "sessionId": session_id,
        "wsPath": f"{config.ws_prefix}/ws/{session_id}",
        "userName": user.given_name or user.user_name,
        "fullName": user.user_name,
        "userEmail": user.user_email,
        "userAvatar": user.user_avatar,
        "permissions": session_info.permissions,
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
        **session_info.config_extra,
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

    sp = config.static_prefix
    css_urls = [
        *session_info.extra_css_urls,
        _hashed_url(sp, "hub-core.css"),
    ]
    js_scripts = [
        _hashed_url(sp, "hub-features.js"),   # phase 1 (first)
        _hashed_url(sp, "hub-ws.js"),          # phase 2
        _hashed_url(sp, "hub-apps.js"),
        _hashed_url(sp, "hub-weather.js"),
        _hashed_url(sp, "hub-mail.js"),
        _hashed_url(sp, "hub-calendar.js"),
        _hashed_url(sp, "hub-news.js"),
        _hashed_url(sp, "hub-stats.js"),
        _hashed_url(sp, "hub-app-core.js"),    # phase 3 (last)
    ]

    html = _build_hub_html(config_json, css_urls, js_scripts, title=config.app_title or "Hub")
    return HTMLResponse(html)
