# LLMing-Hub

A pluggable, real-time dashboard framework for Python web applications.

LLMing-Hub provides a complete landing page / dashboard system with live-updating widgets, application shortcuts, and responsive layout — all driven by pure Python adapters and rendered with zero frontend framework dependencies.

## Features

- **Real-Time Widgets**: Weather, calendar, mail, news, and stats — pushed over WebSocket with change detection.
- **Provider/Adapter Pattern**: Clean separation between data sources (adapters you implement) and UI rendering (built-in providers).
- **Application Grid**: Configurable app cards with icons, links, and permission-based visibility.
- **Responsive Layout**: Multi-column desktop grid that adapts to mobile with horizontal scroll.
- **Dark/Light Theming**: CSS variable-based theming with user toggle and persistent preference.
- **Debug API**: Inspect active sessions, trigger widget refreshes, and fetch data on demand during development.
- **No Frontend Framework**: Pure JavaScript + DOM manipulation — minimal overhead, no build step.

## Architecture

```
External Data Source (O365, Weather API, RSS, ...)
         │
    Adapter (ABC)
    get_weather(), get_inbox(), get_events(), ...
         │
    Provider (BaseProvider subclass)
    fetch_data() → transform to widget JSON
         │
    WebSocket push
    { type: "widget_data", widget_id: "...", data: {...} }
         │
    Frontend Widget (JavaScript)
    onData(data) → render into DOM
```

**Adapters** are abstract interfaces that your application implements. They connect to your actual data sources (Microsoft Graph, weather APIs, RSS feeds, databases).

**Providers** wrap adapters and handle the lifecycle: periodic fetching, hash-based change detection (skip redundant pushes), data transformation, and adaptive polling intervals.

**Widgets** are pure-JS classes that receive data and render HTML. Each extends `HubWidget` with an `onData(data)` method.

## Built-in Widgets

| Widget | Adapter | Refresh | Description |
|--------|---------|---------|-------------|
| **Weather** | `WeatherAdapter` | 10 min | Current conditions, 8-hour forecast, daily outlook. Location dropdown with city override. |
| **Calendar** | `CalendarAdapter` | 120s | Upcoming events with attendee avatars, Teams/online indicators, date grouping. |
| **Mail** | `MailAdapter` | 8s | Inbox summary (total, unread, new today) with message list and hover previews. |
| **News** | `NewsAdapter` | 5 min | Article feed with channel tabs, images, and teaser text. |
| **Stats** | `StatsAdapter` | 30s | Key metrics grid with today/week values, icons, and color coding. |
| **Apps** | Config-driven | Static | Application shortcut cards from session configuration. |

## Installation

```bash
pip install llming-hub
```

Or from source with [Poetry](https://python-poetry.org/):

```bash
git clone https://github.com/Alyxion/llming-hub.git
cd llming-hub
poetry install
```

## Quick Start

```python
from llming_hub import LandingHub, HubConfig, SessionInfo, UserInfo

# 1. Implement your adapters (or use built-in ones)
from my_app.adapters import MyWeatherAdapter, MyCalendarAdapter

# 2. Create a provider factory
def provider_factory(widget_id, session):
    from llming_hub.providers import WeatherWidgetProvider, CalendarWidgetProvider
    if widget_id == "weather":
        return WeatherWidgetProvider(MyWeatherAdapter())
    elif widget_id == "calendar":
        return CalendarWidgetProvider(MyCalendarAdapter())
    return None

# 3. Create a session setup callback
async def session_setup():
    user = get_current_user()  # your auth logic
    if not user:
        return None
    return SessionInfo(
        user=UserInfo(
            user_id=user.id,
            display_name=user.name,
            email=user.email,
        ),
        active_widgets=["weather", "calendar", "mail"],
        apps=[
            {"id": "chat", "label": "Chat", "icon": "chat", "url": "/chat"},
            {"id": "docs", "label": "Documents", "icon": "description", "url": "/docs"},
        ],
    )

# 4. Configure and mount
config = HubConfig(
    app_title="My Dashboard",
    provider_factory=provider_factory,
    session_setup=session_setup,
)

hub = LandingHub(config)
hub.mount(app, route="/")
```

## Implementing an Adapter

Each adapter is an ABC with one or two async methods. Example for weather:

```python
from llming_hub.adapters import WeatherAdapter, WeatherData

class MyWeatherAdapter(WeatherAdapter):
    async def get_weather(self, city: str = "", city_display: str = "") -> WeatherData:
        # Fetch from your weather API
        return WeatherData(
            city="Berlin",
            temperature=22.5,
            condition="Partly Cloudy",
            icon="cloud",
            humidity=65,
            wind_speed=12.0,
            upcoming=[...],  # hourly forecast
            forecast=[...],  # daily forecast
        )
```

Available adapter interfaces:

| Adapter | Methods |
|---------|---------|
| `WeatherAdapter` | `get_weather(city, city_display)` |
| `CalendarAdapter` | `get_events(start, end, limit)` |
| `MailAdapter` | `get_inbox(limit)` |
| `NewsAdapter` | `get_articles(limit, locale)` |
| `StatsAdapter` | `get_stats()` |
| `DirectoryAdapter` | `get_user_by_email(email)`, `get_avatar_url(user_id, w, h)` |

## Configuration

`HubConfig` accepts:

| Parameter | Description |
|-----------|-------------|
| `app_title` | Dashboard title shown in header |
| `logo_url` | Logo image URL |
| `mascot_url` | Optional mascot image for greeting area |
| `accent_color` | Primary accent color (CSS) |
| `bg_dark_url`, `bg_light_url` | Background images for dark/light themes |
| `provider_factory` | `(widget_id, session) → BaseProvider` callback |
| `session_setup` | `() → SessionInfo` async callback for auth + user info |
| `directory` | Optional `DirectoryAdapter` for avatar resolution |
| `data_handlers` | Dict of plugin resource handlers (photos, thumbnails) |
| `debug_auth_dependency` | FastAPI dependency for debug API authentication |

## Debug API

When `debug_auth_dependency` is configured, the following endpoints are available:

```
GET  /api/hub/debug/sessions              # List active sessions
GET  /api/hub/debug/sessions/{id}         # Session detail
POST /api/hub/debug/sessions/{id}/refresh # Trigger widget data push
GET  /api/hub/debug/sessions/{id}/fetch/{widget_id}  # On-demand fetch
```

## Key Design Decisions

- **Change detection**: Providers hash each payload and skip WebSocket pushes when data hasn't changed, reducing network overhead.
- **Adaptive intervals**: Calendar widget accelerates polling (8s) while waiting for directory service resolution, then returns to normal (120s).
- **Per-key resource locking**: The `ResourceCache` uses per-resource locks to prevent thundering-herd when multiple widgets request the same avatar simultaneously.
- **LRU eviction**: Cache eviction is scoped per plugin — one plugin's cache flood won't evict another plugin's entries.

## Frontend Widget API

Custom widgets extend `HubWidget`:

```javascript
class MyWidget extends HubWidget {
  constructor() {
    super('my_widget', {
      icon: 'dashboard',
      titleKey: 'hub.my_widget',
      titleDefault: 'My Widget',
      priority: 50,
    });
  }

  onData(data) {
    this.bodyEl.innerHTML = `<p>${data.message}</p>`;
  }
}

HubFeatures.registerWidget(new MyWidget());
```

Register a matching provider on the backend, and the widget receives live data via WebSocket.

## License

[Business Source License 1.1](LICENSE) — free for organizations with fewer than 20 employees.
Production use by larger organizations requires a [commercial license](LICENSE_COMMERCIAL.md).
Converts to Apache 2.0 four years after each release.
