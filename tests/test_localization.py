from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

from rssbot.i18n import configure_jinja_environment, count_label, translate

PROJECT_DIR = Path(__file__).resolve().parents[1]


def render_template(name: str, **context: object) -> str:
    environment = Environment(
        loader=FileSystemLoader(PROJECT_DIR / "rssbot" / "templates"),
        autoescape=True,
    )
    environment.filters["datetime_utc"] = str
    configure_jinja_environment(environment)
    return environment.get_template(name).render(**context)


class LocalizationTests(unittest.TestCase):
    def test_translates_known_phrases_and_preserves_unknown_content(self) -> None:
        self.assertEqual(translate("Войти через Discord", "en"), "Log in with Discord")
        self.assertEqual(translate("Войти через Discord", "ru"), "Войти через Discord")
        self.assertEqual(translate("Server supplied by Discord", "en"), "Server supplied by Discord")

    def test_home_page_is_localized_in_server_rendered_html(self) -> None:
        rendered = render_template(
            "home.html",
            language="en",
            logged_in=False,
            invite_url="https://discord.com/oauth2/authorize",
            user=None,
            csrf_token="csrf",
            request=SimpleNamespace(query_params={}),
        )

        self.assertIn("News from RSS", rendered)
        self.assertIn("FeedFlow sends only new entries to Discord.", rendered)
        self.assertIn("Log in with Discord", rendered)
        self.assertNotIn("Войти через Discord", rendered)
        self.assertIn('src="/static/local_dates.js"', rendered)
        self.assertNotRegex(rendered, r"[А-Яа-яЁё]")

    def test_landing_copy_explains_that_only_new_entries_are_sent(self) -> None:
        russian = render_template("landing.html", language="ru", invite_url="#")
        english = render_template("landing.html", language="en", invite_url="#")

        self.assertIn("Бот отправляет в Discord только новые записи.", russian)
        self.assertIn("FeedFlow sends only new entries to Discord.", english)
        self.assertNotIn("Первая проверка не отправляет архив.", russian)

    def test_base_document_declares_feedflow_favicon(self) -> None:
        rendered = render_template("base.html", language="ru", logged_in=False, user=None)

        self.assertIn('<link rel="icon" type="image/png" href="/static/feedflow-avatar.png">', rendered)
        self.assertTrue((PROJECT_DIR / "rssbot" / "static" / "feedflow-avatar.png").is_file())

    def test_dashboard_localizes_chrome_without_translating_guild_names(self) -> None:
        rendered = render_template(
            "guild.html",
            language="en",
            guild={"id": "1", "name": "Русский сервер", "icon_url": "", "invite_url": "#"},
            installed=False,
            bot_ready=True,
            feeds=[],
            channels=[],
            notice="Лента удалена",
            error="",
            user=None,
            csrf_token="csrf",
        )

        self.assertIn("Servers", rendered)
        self.assertIn("SERVER SETTINGS", rendered)
        self.assertIn("Feed deleted", rendered)
        self.assertIn("Русский сервер", rendered)
        self.assertNotIn("НАСТРОЙКИ СЕРВЕРА", rendered)

    def test_dashboard_uses_server_localized_count_nouns(self) -> None:
        self.assertEqual(count_label("feed", 1, "en"), "feed")
        self.assertEqual(count_label("feed", 2, "en"), "feeds")
        self.assertEqual(count_label("feed", 1, "ru"), "лента")
        self.assertEqual(count_label("feed", 3, "ru"), "ленты")
        self.assertEqual(count_label("channel", 1, "ru"), "доступный канал")
        self.assertEqual(count_label("channel", 5, "ru"), "доступных каналов")

    def test_feed_form_localizes_labels_on_the_server(self) -> None:
        rendered = render_template(
            "feed_form.html",
            language="en",
            feed=None,
            guild={"id": "1", "name": "Example server"},
            values={
                "title": "Project news",
                "url": "https://example.com/feed.xml",
                "channel_id": "2",
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
            },
            channels=[{"id": "2", "name": "news"}],
            csrf_token="csrf",
            user=None,
            error="",
            placeholder_tags="{title}, {url}, {description}",
        )

        self.assertIn("Customize the post embed", rendered)
        self.assertIn("Message above the embed — optional", rendered)
        self.assertIn("Find RSS/Atom feed", rendered)
        self.assertNotIn("Настройте карточку публикации", rendered)
        self.assertNotIn("Найти RSS/Atom", rendered)
        self.assertNotRegex(rendered, r"[А-Яа-яЁё]")

    def test_template_guide_and_test_picker_render_in_english(self) -> None:
        guide = render_template("template_help.html", language="en", user=None, csrf_token="csrf")
        picker = render_template(
            "test_select.html",
            language="en",
            feed={"id": "feed-1", "title": "Project news"},
            guild={"id": "1", "name": "Example server"},
            entries=[
                {
                    "key": "entry-1",
                    "title": "An update",
                    "description": "A short summary",
                    "published_at": 1_792_599_000,
                    "url": "https://example.com/post",
                }
            ],
            error="",
            user=None,
            csrf_token="csrf",
        )

        self.assertIn("Post template tags", guide)
        self.assertIn("Read on the website", guide)
        self.assertNotIn("Порядок блоков, разделители", guide)
        self.assertIn("Choose a post to test", picker)
        self.assertNotIn("Выберите новость для теста", picker)
        self.assertNotRegex(guide, r"[А-Яа-яЁё]")
        self.assertNotRegex(picker, r"[А-Яа-яЁё]")

    def test_browser_script_only_localizes_dates(self) -> None:
        script = (PROJECT_DIR / "rssbot" / "static" / "local_dates.js").read_text(encoding="utf-8")

        self.assertIn("Intl.DateTimeFormat", script)
        self.assertNotIn("const phrases", script)
        self.assertNotIn("createTreeWalker", script)


if __name__ == "__main__":
    unittest.main()
