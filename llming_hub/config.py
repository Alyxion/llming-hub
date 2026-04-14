"""Hub configuration dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class AppDef:
    """Definition of an application card shown on the hub."""
    name: str
    icon: str
    route: str


@dataclass
class WidgetDef:
    """Definition of a widget shown on the hub."""
    widget_id: str
    title: str
    icon: str
    external_url: str = ""
    interval: float = 60.0


@dataclass
class UserInfo:
    """User information returned by the session_setup callback."""
    user_id: str
    user_name: str
    given_name: str = ""
    user_email: str = ""
    user_avatar: str = ""
    locale: str = "en-us"


@dataclass
class SessionInfo:
    """Result of the session_setup callback — everything the hub page needs."""
    user: UserInfo
    active_widgets: list[str] = field(default_factory=list)
    apps: list[dict] = field(default_factory=list)
    i18n: dict[str, str] = field(default_factory=dict)
    greeting: str = ""
    banner_html: str = ""
    version: str = ""
    copyright: str = ""
    permissions: list[str] = field(default_factory=list)  # PERM_* constants
    admin_url: str = ""
    settings_url: str = ""
    dev_overrides: bool = False
    dev_overrides_label: str = ""
    dev_overrides_url: str = ""
    extra_css_urls: list[str] = field(default_factory=list)
    config_extra: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class HubConfig:
    """Configuration for the hub landing page."""

    # Branding
    app_title: str = "Hub"
    logo_url: str = ""
    footer_text: str = ""
    accent_color: str = "#4B8FE7"
    footer_bg_color: str = "#1a1a2e"
    bg_dark_url: str = ""
    bg_light_url: str = ""
    mascot_url: str = ""

    # Provider factory — consuming app provides this
    # Signature: (widget_id: str, session: HubSessionEntry) -> BaseProvider | None
    provider_factory: Optional[Callable] = None

    # Directory adapter — unified identity + avatar service
    directory: Any = None  # DirectoryAdapter

    # Session setup callback — consuming app provides auth + user info
    # Signature: async (request) -> SessionInfo | None
    session_setup: Optional[Callable] = None

    # OAuth start handler — called when session_setup returns None
    # Signature: async (request) -> Response (redirect to OAuth provider)
    # If not set, stale cookies are cleared and the page redirects to itself.
    oauth_start_handler: Optional[Callable] = None

    # OAuth callback handler — called when /?code=... arrives from the provider
    # Signature: async (request) -> Response (exchange code, set cookies, redirect)
    oauth_callback_handler: Optional[Callable] = None

    # Debug API security dependency (FastAPI Depends)
    debug_auth_dependency: Optional[Callable] = None

    # Static file prefix (auto-set during mount)
    static_prefix: str = "/llming-hub-static"

    # WS API prefix
    ws_prefix: str = "/api/hub"

    # Data endpoint — plugin handlers for photos, thumbnails, etc.
    data_handlers: dict[str, Any] = field(default_factory=dict)
    data_prefix: str = "/api/hub/data"
