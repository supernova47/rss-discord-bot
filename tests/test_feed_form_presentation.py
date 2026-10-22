from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path

from fastapi.templating import Jinja2Templates

from rssbot.i18n import configure_jinja_environment

PROJECT_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(PROJECT_DIR / "rssbot" / "templates"))
configure_jinja_environment(templates.env)


class FeedFormState(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.details_stack: list[bool] = []
        self.advanced_open: list[bool] = []
        self.fields: dict[str, list[bool]] = {}
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(str(attributes["id"]))
        if tag == "details":
            is_advanced = "advanced-settings" in (attributes.get("class") or "").split()
            self.details_stack.append(is_advanced)
            if is_advanced:
                self.advanced_open.append("open" in attributes)
        elif tag in {"input", "select", "textarea"} and attributes.get("name"):
            field_name = str(attributes["name"])
            self.fields.setdefault(field_name, []).append(any(self.details_stack))

    def handle_endtag(self, tag: str) -> None:
        if tag == "details" and self.details_stack:
            self.details_stack.pop()


def render_form(*, feed: dict[str, str] | None = None, error: str = "") -> str:
    values = {
        "title": "Project news",
        "url": "https://example.com/feed.xml",
        "channel_id": "456",
        "interval_minutes": 5,
        "display_name": "News",
        "avatar_url": "",
        "avatar_preview_url": "",
        "avatar_data": None,
        "embed_title_template": "{title}",
        "embed_description_template": "{description}",
        "message_template": "",
        "embed_color_hex": "#5865F2",
        "layout_order": "title,media,description,buttons",
        "buttons": [],
        "timestamp_style": "both",
        "show_image": False,
    }
    return templates.env.get_template("feed_form.html").render(
        language="ru",
        feed=feed,
        guild={"id": "123", "name": "Test server", "icon_url": ""},
        values=values,
        channels=[{"id": "456", "name": "news"}],
        csrf_token="csrf-token",
        user=None,
        error=error,
        placeholder_tags="{title}, {url}, {description}",
    )


class FeedFormPresentationTests(unittest.TestCase):
    def test_new_feed_keeps_core_fields_visible_and_collapses_optional_settings(self) -> None:
        parser = FeedFormState()
        parser.feed(render_form())

        self.assertEqual(parser.advanced_open, [False])
        for field_name in ("title", "url", "channel_id"):
            self.assertEqual(parser.fields[field_name], [False])
        for field_name in ("interval_minutes", "display_name", "embed_title_template"):
            self.assertEqual(parser.fields[field_name], [True])

    def test_editing_feed_expands_optional_settings(self) -> None:
        parser = FeedFormState()
        parser.feed(render_form(feed={"id": "feed-1"}))

        self.assertEqual(parser.advanced_open, [True])

    def test_form_with_validation_error_expands_optional_settings(self) -> None:
        parser = FeedFormState()
        parser.feed(render_form(error="Invalid feed URL"))

        self.assertEqual(parser.advanced_open, [True])

    def test_preview_has_targets_for_entry_media(self) -> None:
        parser = FeedFormState()
        parser.feed(render_form())

        media_preview_ids = {"preview-image-note", "preview-image-message", "preview-image", "preview-video"}
        self.assertTrue(media_preview_ids.issubset(parser.ids))


if __name__ == "__main__":
    unittest.main()
