from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path

from fastapi.templating import Jinja2Templates

from rssbot.i18n import configure_jinja_environment

PROJECT_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(PROJECT_DIR / "rssbot" / "templates"))
configure_jinja_environment(templates.env)


class FeedListMarkup(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: dict[str, dict[str, str | None]] = {}
        self.feed_rows: list[dict[str, str | None]] = []
        self.classes: set[str] = set()
        self.text: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids[str(element_id)] = attributes
        classes = (attributes.get("class") or "").split()
        self.classes.update(classes)
        if tag == "article" and "feed-row" in classes:
            self.feed_rows.append(attributes)
        if tag == "a" and attributes.get("href"):
            self.links.append(str(attributes["href"]))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def render_dashboard() -> str:
    feeds = [
        {
            "id": "feed-1",
            "title": 'Новости & "обновления"',
            "url": "https://example.com/news.xml?a=1&b=2",
            "channel_id": "123",
            "channel_name": "news-updates",
            "interval_minutes": 5,
            "avatar_preview_url": "",
            "is_active": True,
            "last_error": "HTTP 429: site rate limited requests",
            "initialized": True,
            "last_success_at": None,
        },
        {
            "id": "feed-2",
            "title": "Paused feed",
            "url": "https://example.com/paused.xml",
            "channel_id": "456",
            "channel_name": "announcements",
            "interval_minutes": 15,
            "avatar_preview_url": "",
            "is_active": False,
            "last_error": "",
            "initialized": True,
            "last_success_at": None,
        },
    ]
    return templates.env.get_template("guild.html").render(
        language="ru",
        guild={"id": 99, "name": "Example server", "icon_url": ""},
        installed=True,
        bot_ready=True,
        feeds=feeds,
        channels=[],
        notice="",
        error="",
        user=None,
        csrf_token="csrf-token",
    )


class FeedListPresentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = FeedListMarkup()
        self.parser.feed(render_dashboard())

    def test_dashboard_renders_accessible_search_filters_count_and_reset(self) -> None:
        for element_id in (
            "feed-search",
            "feed-status-filter",
            "feed-channel-filter",
            "feed-result-count",
            "feed-filter-reset",
            "feed-filter-empty",
            "feed-list",
        ):
            self.assertIn(element_id, self.parser.ids)

        self.assertIn("hidden", self.parser.ids["feed-filter-empty"])
        self.assertEqual(self.parser.ids["feed-search"].get("type"), "search")
        self.assertEqual(self.parser.ids["feed-result-count"].get("aria-live"), "polite")

    def test_rows_expose_search_and_status_data_and_keep_feed_actions(self) -> None:
        self.assertEqual(len(self.parser.feed_rows), 2)
        error_feed, paused_feed = self.parser.feed_rows

        self.assertEqual(error_feed.get("data-feed-title"), 'Новости & "обновления"')
        self.assertEqual(error_feed.get("data-feed-url"), "https://example.com/news.xml?a=1&b=2")
        self.assertEqual(error_feed.get("data-channel-name"), "news-updates")
        self.assertEqual(error_feed.get("data-channel-id"), "123")
        self.assertEqual(error_feed.get("data-active"), "true")
        self.assertEqual(error_feed.get("data-has-error"), "true")
        self.assertEqual(paused_feed.get("data-active"), "false")
        self.assertEqual(paused_feed.get("data-has-error"), "false")
        self.assertIn("/guilds/99/feeds/feed-1/test", self.parser.links)
        self.assertIn("/guilds/99/feeds/feed-1/edit", self.parser.links)

    def test_feed_error_keeps_original_message_and_shows_recovery_hint(self) -> None:
        rendered_text = "".join(self.parser.text)

        self.assertIn("feed-error-card", self.parser.classes)
        self.assertIn("Последняя ошибка: HTTP 429: site rate limited requests", rendered_text)
        self.assertIn("Проверьте текст ошибки, адрес ленты и канал", rendered_text)


if __name__ == "__main__":
    unittest.main()
