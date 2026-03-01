"""Adapter ABCs and data models for llming-hub."""

from llming_hub.adapters.directory import DirectoryAdapter, DirectoryUser
from llming_hub.adapters.mail import MailAdapter, MailInbox, MailMessage
from llming_hub.adapters.calendar import CalendarAdapter, CalEvent, CalAttendee
from llming_hub.adapters.weather import WeatherAdapter, WeatherData, WeatherHourForecast, WeatherDayForecast
from llming_hub.adapters.news import NewsAdapter, NewsArticle
from llming_hub.adapters.stats import StatsAdapter, StatsRow

__all__ = [
    "DirectoryAdapter", "DirectoryUser",
    "MailAdapter", "MailInbox", "MailMessage",
    "CalendarAdapter", "CalEvent", "CalAttendee",
    "WeatherAdapter", "WeatherData", "WeatherHourForecast", "WeatherDayForecast",
    "NewsAdapter", "NewsArticle",
    "StatsAdapter", "StatsRow",
]
