from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

import aiohttp
import discord
from cryptography.fernet import Fernet, InvalidToken
from discord import app_commands
from discord.ext import commands

from rssbot.config import Settings
from rssbot.db import Database
from rssbot.fetcher import FeedFetcher, FeedFetchError
from rssbot.formatting import (
    SEPARATOR_BLOCK,
    discord_timestamp,
    entry_values,
    parse_layout_order,
    parse_link_buttons,
    render_template,
)

log = logging.getLogger("rssbot")
DEFAULT_WEBHOOK_NAME = "RSS Feeds"
DISCONNECT_ALERT_DELAY_SECONDS = 15
MOSCOW_TIMEZONE = timezone(timedelta(hours=3), "MSK")
RUSSIAN_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def _format_moscow_timestamp(value: datetime | None = None) -> str:
    now = (value or datetime.now(UTC)).astimezone(MOSCOW_TIMEZONE)
    return f"{now.day} {RUSSIAN_MONTHS[now.month - 1]} {now.year} г., {now:%H:%M} МСК"


class RSSRuntime:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        self._fernet = Fernet(settings.webhook_encryption_key.encode("ascii"))
        intents = discord.Intents.none()
        intents.guilds = True
        self.bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
        self.bot.tree.add_command(self._create_command_group())
        self.fetcher: FeedFetcher | None = None
        self.webhook_session: aiohttp.ClientSession | None = None
        self._bot_task: asyncio.Task[None] | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._feed_locks: dict[str, asyncio.Lock] = {}
        self._webhook_locks: dict[int, asyncio.Lock] = {}
        self._feed_webhook_locks: dict[str, asyncio.Lock] = {}
        self._webhook_cache: dict[int, discord.Webhook] = {}
        self._feed_webhook_cache: dict[str, discord.Webhook] = {}
        self._ready = asyncio.Event()
        self._disconnect_started_at: float | None = None
        self._disconnect_timestamp: datetime | None = None
        self._disconnect_alert_task: asyncio.Task[None] | None = None
        self._disconnect_recovery_in_progress = False
        self._shutting_down = False
        self._register_events()

    @property
    def ready(self) -> bool:
        return self._ready.is_set() and self.bot.is_ready()

    def _register_events(self) -> None:
        @self.bot.event
        async def on_ready() -> None:
            await self._mark_connected()
            log.info("Discord-бот подключён как %s", self.bot.user)
            try:
                if self.settings.dev_guild_id:
                    guild = discord.Object(id=self.settings.dev_guild_id)
                    self.bot.tree.copy_global_to(guild=guild)
                    await self.bot.tree.sync(guild=guild)
                else:
                    await self.bot.tree.sync()
            except discord.HTTPException:
                log.exception("Не удалось обновить slash-команды")

        @self.bot.event
        async def on_disconnect() -> None:
            was_ready = self._ready.is_set()
            self._ready.clear()
            log.warning("Discord-бот потерял соединение; выполняется повторное подключение")
            if was_ready and not self._shutting_down and self._disconnect_started_at is None:
                disconnected_at = time.monotonic()
                self._disconnect_started_at = disconnected_at
                self._disconnect_timestamp = datetime.now(UTC)
                self._disconnect_alert_task = asyncio.create_task(
                    self._send_disconnect_alert_after_delay(disconnected_at),
                    name="discord-disconnect-alert",
                )

        @self.bot.event
        async def on_resumed() -> None:
            await self._mark_connected(resumed=True)

    async def _mark_connected(self, *, resumed: bool = False) -> None:
        self._ready.set()
        disconnected_at = self._disconnect_started_at
        if disconnected_at is None:
            return
        if self._disconnect_recovery_in_progress:
            return

        duration = max(0, int(time.monotonic() - disconnected_at))
        alert_task = self._disconnect_alert_task
        if duration < DISCONNECT_ALERT_DELAY_SECONDS:
            # A brief gateway reconnect is normal; don't send either half of an alert pair.
            self._clear_disconnect_state()
            if alert_task is not None and not alert_task.done():
                alert_task.cancel()
                await asyncio.gather(alert_task, return_exceptions=True)
            log.info(
                "Discord-бот восстановил соединение после краткого сбоя "
                "(%s сек.); уведомление пропущено",
                duration,
            )
            return

        self._disconnect_recovery_in_progress = True
        if alert_task is not None:
            await asyncio.gather(alert_task, return_exceptions=True)
        else:
            await self._send_disconnect_alert()

        self._clear_disconnect_state()
        if duration < 60:
            duration_text = f"{duration} сек."
        elif duration < 3600:
            duration_text = f"{duration // 60} мин. {duration % 60} сек."
        else:
            duration_text = f"{duration // 3600} ч. {(duration % 3600) // 60} мин."
        timestamp = _format_moscow_timestamp()
        event = "восстановил" if resumed else "подключился"
        await self._send_telegram_alert(
            f"✅ FeedFlow {event} к Discord.\n"
            f"Время: {timestamp}\n"
            f"Длительность сбоя: {duration_text}"
        )
        log.info("Discord-бот восстановил соединение после сбоя длительностью %s", duration_text)

    async def _send_disconnect_alert_after_delay(self, disconnected_at: float) -> None:
        await asyncio.sleep(DISCONNECT_ALERT_DELAY_SECONDS)
        if self._shutting_down or self._disconnect_started_at != disconnected_at:
            return
        await self._send_disconnect_alert()

    async def _send_disconnect_alert(self) -> None:
        timestamp = _format_moscow_timestamp(self._disconnect_timestamp)
        await self._send_telegram_alert(
            f"⚠️ FeedFlow потерял соединение с Discord.\n"
            f"Время: {timestamp}\n"
            "Бот пытается переподключиться."
        )

    def _clear_disconnect_state(self) -> None:
        self._disconnect_started_at = None
        self._disconnect_timestamp = None
        self._disconnect_alert_task = None
        self._disconnect_recovery_in_progress = False

    async def _send_telegram_alert(self, message: str) -> None:
        token = self.settings.telegram_alert_bot_token
        chat_id = self.settings.telegram_alert_chat_id
        if not token or not chat_id:
            return
        if self.webhook_session is None:
            log.warning("Не удалось отправить Telegram-уведомление: HTTP-сессия ещё не запущена")
            return

        try:
            async with self.webhook_session.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message},
                timeout=aiohttp.ClientTimeout(total=8, connect=4),
            ) as response:
                if response.status != 200:
                    log.warning("Telegram отклонил уведомление (HTTP %s)", response.status)
                else:
                    log.info("Telegram-уведомление о состоянии Discord отправлено")
        except (TimeoutError, aiohttp.ClientError) as exc:
            log.warning("Не удалось отправить Telegram-уведомление (%s)", type(exc).__name__)

    def _create_command_group(self) -> app_commands.Group:
        group = app_commands.Group(name="rss", description="Управление RSS-лентами на сервере")

        @group.command(name="list", description="Показать RSS-ленты сервера")
        @app_commands.checks.has_permissions(manage_guild=True)
        async def list_feeds(interaction: discord.Interaction) -> None:
            if interaction.guild_id is None:
                await interaction.response.send_message("Команда работает на сервере.", ephemeral=True)
                return
            feeds = await self.db.get_feeds_for_guild(interaction.guild_id)
            if not feeds:
                await interaction.response.send_message("На этом сервере пока нет RSS-лент.", ephemeral=True)
                return
            lines = []
            for feed in feeds[:25]:
                status = "включена" if feed["is_active"] else "на паузе"
                error = f" · ошибка: {feed['last_error'][:100]}" if feed["last_error"] else ""
                lines.append(f"`{feed['id']}` · **{feed['title']}** · {status}{error}")
            embed = discord.Embed(title="RSS-ленты", description="\n".join(lines), color=0x5865F2)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @group.command(name="test", description="Отправить тестовую карточку RSS-ленты")
        @app_commands.describe(feed_id="Короткий ID ленты из списка /rss list")
        @app_commands.checks.has_permissions(manage_guild=True)
        async def test_feed(interaction: discord.Interaction, feed_id: str) -> None:
            feed = await self.db.get_feed(feed_id.strip())
            if feed is None or interaction.guild_id is None or feed["guild_id"] != str(interaction.guild_id):
                await interaction.response.send_message("Лента не найдена на этом сервере.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True, thinking=True)
            try:
                await self.send_test(feed)
            except Exception as exc:
                log.exception("Ошибка тестовой отправки ленты %s", feed_id)
                await interaction.followup.send(
                    f"Не удалось отправить тест: {str(exc)[:300]}", ephemeral=True
                )
            else:
                await interaction.followup.send("Тестовая карточка отправлена.", ephemeral=True)

        @group.command(name="toggle", description="Включить или поставить ленту на паузу")
        @app_commands.describe(feed_id="Короткий ID ленты из списка /rss list")
        @app_commands.checks.has_permissions(manage_guild=True)
        async def toggle_feed(interaction: discord.Interaction, feed_id: str) -> None:
            feed = await self.db.get_feed(feed_id.strip())
            if feed is None or interaction.guild_id is None or feed["guild_id"] != str(interaction.guild_id):
                await interaction.response.send_message("Лента не найдена на этом сервере.", ephemeral=True)
                return
            updated = await self.db.toggle_feed(feed_id.strip())
            state = "включена" if updated and updated["is_active"] else "поставлена на паузу"
            await interaction.response.send_message(f"Лента **{feed['title']}** {state}.", ephemeral=True)

        return group

    async def start(self) -> None:
        self.fetcher = FeedFetcher()
        self.webhook_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25, connect=10))
        self._bot_task = asyncio.create_task(self._run_bot(), name="discord-gateway")
        self._poll_task = asyncio.create_task(self._poll_loop(), name="rss-poller")

    async def _run_bot(self) -> None:
        try:
            await self.bot.start(self.settings.bot_token)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Discord-бот завершился с ошибкой")

    async def close(self) -> None:
        self._shutting_down = True
        if self._disconnect_alert_task is not None and not self._disconnect_alert_task.done():
            self._disconnect_alert_task.cancel()
            await asyncio.gather(self._disconnect_alert_task, return_exceptions=True)
        self._clear_disconnect_state()
        for task in (self._poll_task, self._bot_task):
            if task is not None:
                task.cancel()
        for task in (self._poll_task, self._bot_task):
            if task is not None:
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        await self.bot.close()
        if self.fetcher is not None:
            await self.fetcher.close()
        if self.webhook_session is not None:
            await self.webhook_session.close()

    def installed_guild(self, guild_id: int) -> discord.Guild | None:
        return self.bot.get_guild(guild_id)

    def channels_for(self, guild_id: int) -> list[discord.TextChannel]:
        guild = self.installed_guild(guild_id)
        if guild is None or guild.me is None:
            return []
        channels = [
            channel
            for channel in guild.text_channels
            if (permissions := channel.permissions_for(guild.me)).view_channel and permissions.manage_webhooks
        ]
        return sorted(channels, key=lambda channel: (channel.position, channel.name.casefold()))

    async def ensure_channel_webhook(self, channel_id: int) -> discord.Webhook:
        lock = self._webhook_locks.setdefault(channel_id, asyncio.Lock())
        async with lock:
            cached = self._webhook_cache.get(channel_id)
            if cached is not None:
                return cached
            webhook = await self._get_or_create_channel_webhook(channel_id)
            self._webhook_cache[channel_id] = webhook
            return webhook

    async def _get_or_create_channel_webhook(self, channel_id: int) -> discord.Webhook:
        if self.webhook_session is None or not self.ready:
            raise RuntimeError("Бот ещё подключается к Discord. Подождите немного и повторите.")
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            raise RuntimeError("Выберите текстовый канал сервера")
        guild = channel.guild
        if guild.me is None:
            raise RuntimeError("Не удалось проверить права бота на выбранный канал")
        perms = channel.permissions_for(guild.me)
        if not perms.view_channel or not perms.manage_webhooks:
            raise RuntimeError("Боту нужны права View Channel и Manage Webhooks в этом канале")

        existing = await self.db.get_webhook(channel_id)
        if existing is not None:
            try:
                token = self._fernet.decrypt(existing["token_encrypted"].encode("ascii")).decode("utf-8")
                webhook = discord.Webhook.partial(
                    id=int(existing["webhook_id"]), token=token, session=self.webhook_session
                )
                await webhook.fetch()
                return webhook
            except (InvalidToken, ValueError):
                await self.db.delete_webhook(channel_id)
            except discord.NotFound:
                await self.db.delete_webhook(channel_id)
            except discord.Forbidden:
                await self.db.delete_webhook(channel_id)
            except discord.HTTPException as exc:
                if exc.status not in {401, 404}:
                    raise
                await self.db.delete_webhook(channel_id)

        hooks = await channel.webhooks()
        bot_id = self.bot.user.id if self.bot.user else 0
        hook = next(
            (
                item
                for item in hooks
                if item.token
                and (item.application_id == bot_id or (item.user is not None and item.user.id == bot_id))
            ),
            None,
        )
        if hook is None:
            hook = await channel.create_webhook(
                name=DEFAULT_WEBHOOK_NAME,
                reason="Создание канала доставки RSS-новостей",
            )
        if not hook.token:
            raise RuntimeError("Discord не вернул токен вебхука. Пересоздайте вебхук в настройках канала.")
        encrypted = self._fernet.encrypt(hook.token.encode("utf-8")).decode("ascii")
        await self.db.save_webhook(channel_id, hook.id, encrypted)
        return discord.Webhook.partial(id=hook.id, token=hook.token, session=self.webhook_session)

    async def ensure_feed_webhook(
        self, feed: dict[str, Any], *, update_avatar: bool = False
    ) -> discord.Webhook:
        """Use a dedicated webhook only for feeds with an uploaded avatar."""
        avatar_data = feed.get("avatar_data")
        if not avatar_data:
            await self.delete_feed_webhook(str(feed["id"]))
            return await self.ensure_channel_webhook(int(feed["channel_id"]))

        feed_id = str(feed["id"])
        lock = self._feed_webhook_locks.setdefault(feed_id, asyncio.Lock())
        async with lock:
            channel_id = int(feed["channel_id"])
            cached = self._feed_webhook_cache.get(feed_id)
            if cached is not None:
                saved = await self.db.get_feed_webhook(feed_id)
                if saved is not None and saved["channel_id"] == str(channel_id):
                    if update_avatar:
                        await cached.edit(avatar=bytes(avatar_data))
                    return cached
                self._feed_webhook_cache.pop(feed_id, None)
            if self.webhook_session is None or not self.ready:
                raise RuntimeError("Бот ещё подключается к Discord. Подождите немного и повторите.")

            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                raise RuntimeError("Выберите текстовый канал сервера")
            if channel.guild.me is None:
                raise RuntimeError("Не удалось проверить права бота на выбранный канал")
            perms = channel.permissions_for(channel.guild.me)
            if not perms.view_channel or not perms.manage_webhooks:
                raise RuntimeError("Боту нужны права View Channel и Manage Webhooks в этом канале")

            existing = await self.db.get_feed_webhook(feed_id)
            if existing is not None and existing["channel_id"] == str(channel_id):
                try:
                    token = self._fernet.decrypt(existing["token_encrypted"].encode("ascii")).decode("utf-8")
                    webhook = discord.Webhook.partial(
                        id=int(existing["webhook_id"]), token=token, session=self.webhook_session
                    )
                    await webhook.fetch()
                    if update_avatar:
                        await webhook.edit(avatar=bytes(avatar_data))
                    self._feed_webhook_cache[feed_id] = webhook
                    return webhook
                except (InvalidToken, ValueError, discord.NotFound, discord.Forbidden):
                    await self.db.delete_feed_webhook(feed_id)
                except discord.HTTPException as exc:
                    if exc.status not in {401, 404}:
                        raise
                    await self.db.delete_feed_webhook(feed_id)
            elif existing is not None:
                try:
                    old_token = self._fernet.decrypt(
                        existing["token_encrypted"].encode("ascii")
                    ).decode("utf-8")
                    old_webhook = discord.Webhook.partial(
                        id=int(existing["webhook_id"]), token=old_token, session=self.webhook_session
                    )
                    await old_webhook.delete()
                except (InvalidToken, ValueError, discord.NotFound, discord.Forbidden):
                    pass
                except discord.HTTPException as exc:
                    if exc.status not in {401, 404}:
                        log.warning("Не удалось удалить старый вебхук ленты %s: %s", feed_id, exc)
                await self.db.delete_feed_webhook(feed_id)

            hook = await channel.create_webhook(
                name=(str(feed.get("display_name") or feed.get("title") or "RSS Feed")[:80]),
                avatar=bytes(avatar_data),
                reason="Создание вебхука с аватаром RSS-ленты",
            )
            if not hook.token:
                raise RuntimeError("Discord не вернул токен вебхука. Проверьте права Manage Webhooks.")
            encrypted = self._fernet.encrypt(hook.token.encode("utf-8")).decode("ascii")
            await self.db.save_feed_webhook(feed_id, channel_id, hook.id, encrypted)
            webhook = discord.Webhook.partial(id=hook.id, token=hook.token, session=self.webhook_session)
            self._feed_webhook_cache[feed_id] = webhook
            return webhook

    async def delete_feed_webhook(self, feed_id: str) -> None:
        lock = self._feed_webhook_locks.setdefault(feed_id, asyncio.Lock())
        if lock.locked():
            # The caller may already be synchronizing this feed's webhook.
            self._feed_webhook_cache.pop(feed_id, None)
            await self.db.delete_feed_webhook(feed_id)
            return
        async with lock:
            self._feed_webhook_cache.pop(feed_id, None)
            existing = await self.db.get_feed_webhook(feed_id)
            if existing is not None and self.webhook_session is not None:
                try:
                    token = self._fernet.decrypt(existing["token_encrypted"].encode("ascii")).decode("utf-8")
                    webhook = discord.Webhook.partial(
                        id=int(existing["webhook_id"]), token=token, session=self.webhook_session
                    )
                    await webhook.delete()
                except (InvalidToken, ValueError, discord.NotFound, discord.Forbidden):
                    pass
                except discord.HTTPException as exc:
                    if exc.status not in {401, 404}:
                        log.warning("Не удалось удалить вебхук ленты %s: %s", feed_id, exc)
            await self.db.delete_feed_webhook(feed_id)

    @staticmethod
    def _make_layout_view(
        feed: dict[str, Any], entry: dict[str, Any], values: dict[str, str], content: str
    ) -> discord.ui.LayoutView:
        """Build a Components V2 card with an optional media block and local timestamp."""
        view = discord.ui.LayoutView(timeout=None)
        if content:
            view.add_item(discord.ui.TextDisplay(content[:4000]))

        title = render_template(feed["embed_title_template"], values, limit=256)
        description = render_template(feed["embed_description_template"], values, limit=4096)
        title_text = title
        media_url = str(entry.get("media") or entry.get("image") or "")
        media_scheme = urlsplit(media_url).scheme
        if not feed.get("show_image") or media_scheme not in {"http", "https"}:
            media_url = ""

        title_component = discord.ui.TextDisplay(title_text) if title_text else None
        description_component = discord.ui.TextDisplay(description) if description else None
        media_component = (
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media=media_url,
                    description=title[:1024] or None,
                )
            )
            if media_url
            else None
        )
        link_buttons = discord.ui.ActionRow()
        for button in parse_link_buttons(feed.get("buttons_json", "[]")):
            button_url = render_template(button["url"], values, limit=513)
            try:
                parsed_button_url = urlsplit(button_url)
            except ValueError:
                continue
            if (
                len(button_url) > 512
                or parsed_button_url.scheme not in {"http", "https"}
                or not parsed_button_url.hostname
                or parsed_button_url.username
                or parsed_button_url.password
            ):
                continue
            link_buttons.add_item(
                discord.ui.Button(
                    style=discord.ButtonStyle.link,
                    label=button["label"],
                    url=button_url,
                )
            )
        button_component = link_buttons if link_buttons.children else None
        components = {
            "title": title_component,
            "media": media_component,
            "description": description_component,
            "buttons": button_component,
        }
        children = []
        layout_has_content = False
        trailing_separator = False
        for block in parse_layout_order(feed.get("layout_order")):
            if block == SEPARATOR_BLOCK:
                if layout_has_content and not trailing_separator:
                    children.append(discord.ui.Separator())
                    trailing_separator = True
                continue
            component = components[block]
            if component is None:
                continue
            children.append(component)
            layout_has_content = True
            trailing_separator = False

        feed_title = str(feed.get("title", "")).strip()
        published = discord_timestamp(entry.get("published_at"), feed.get("timestamp_style", "both"))
        footer = " · ".join(part for part in (feed_title, published) if part)
        if footer:
            children.append(discord.ui.TextDisplay(f"-# {footer}"[:4000]))

        view.add_item(
            discord.ui.Container(
                *children,
                accent_colour=discord.Color(int(feed["embed_color"])),
            )
        )
        return view

    async def send_entry(self, feed: dict[str, Any], entry: dict[str, Any]) -> discord.Message:
        has_uploaded_avatar = bool(feed.get("avatar_data"))
        webhook = (
            await self.ensure_feed_webhook(feed)
            if has_uploaded_avatar
            else await self.ensure_channel_webhook(int(feed["channel_id"]))
        )
        values = entry_values(feed, entry)
        content = render_template(feed["message_template"], values, limit=2000)
        title = render_template(feed["embed_title_template"], values, limit=256)
        description = render_template(feed["embed_description_template"], values, limit=4096)
        media_url = str(entry.get("media") or entry.get("image") or "")
        has_media = feed["show_image"] and urlsplit(media_url).scheme in {"http", "https"}
        has_buttons = bool(parse_link_buttons(feed.get("buttons_json", "[]")))
        if not content and not title and not description and not has_media and not has_buttons:
            raise RuntimeError("Шаблон не сформировал сообщение. Проверьте текст и поля карточки.")
        view = self._make_layout_view(feed, entry, values, content)
        display_name = (str(feed["display_name"]).strip() or str(feed["title"]))[:80]
        avatar_url = str(feed.get("avatar_url") or "").strip()
        if avatar_url and urlsplit(avatar_url).scheme != "https":
            raise RuntimeError("Ссылка на аватар должна начинаться с https://")
        payload = {
            "username": display_name,
            "avatar_url": (None if has_uploaded_avatar else avatar_url or None),
            "allowed_mentions": discord.AllowedMentions.none(),
            "wait": True,
        }
        payload["view"] = view
        try:
            return await webhook.send(**payload)
        except (discord.NotFound, discord.Forbidden):
            if has_uploaded_avatar:
                self._feed_webhook_cache.pop(str(feed["id"]), None)
                await self.db.delete_feed_webhook(str(feed["id"]))
                replacement = await self.ensure_feed_webhook(feed)
            else:
                lock = self._webhook_locks.setdefault(int(feed["channel_id"]), asyncio.Lock())
                async with lock:
                    self._webhook_cache.pop(int(feed["channel_id"]), None)
                    await self.db.delete_webhook(int(feed["channel_id"]))
                replacement = await self.ensure_channel_webhook(int(feed["channel_id"]))
            return await replacement.send(**payload)

    async def fetch_test_entries(self, feed: dict[str, Any]) -> list[dict[str, Any]]:
        if self.fetcher is None:
            raise RuntimeError("Загрузчик RSS ещё не запущен. Повторите попытку через несколько секунд.")
        result = await self.fetcher.fetch(str(feed["url"]))
        return sorted(
            result.entries,
            key=lambda item: item.get("published_at") or 0,
            reverse=True,
        )[:10]

    async def send_test(self, feed: dict[str, Any], entry: dict[str, Any] | None = None) -> discord.Message:
        if entry is None:
            entries = await self.fetch_test_entries(feed)
            if not entries:
                raise RuntimeError("В RSS-ленте пока нет записей для тестовой отправки.")
            entry = entries[0]
        return await self.send_entry(feed, entry)

    async def _poll_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.settings.poll_seconds)
                if not self.ready or self.fetcher is None:
                    continue
                due = await self.db.due_feeds()
                if due:
                    semaphore = asyncio.Semaphore(4)
                    await asyncio.gather(*(self._poll_with_semaphore(feed, semaphore) for feed in due))
                await self.db.delete_expired_sessions()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Ошибка цикла проверки RSS-лент")

    async def _poll_with_semaphore(self, feed: dict[str, Any], semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            await self._poll_feed(feed)

    async def _poll_feed(self, feed: dict[str, Any]) -> None:
        lock = self._feed_locks.setdefault(feed["id"], asyncio.Lock())
        if lock.locked():
            return
        async with lock:
            feed = await self.db.get_feed(feed["id"])
            if feed is None or not feed["is_active"]:
                return
            assert self.fetcher is not None
            now = time.time()
            interval = int(feed["interval_seconds"])
            try:
                result = await self.fetcher.fetch(
                    feed["url"], etag=feed["etag"], last_modified=feed["last_modified"]
                )
                await self.db.set_poll_success(
                    feed["id"],
                    next_poll_at=now + interval,
                    etag=result.etag,
                    last_modified=result.last_modified,
                )
                if result.not_modified or not result.entries:
                    return

                entries = result.entries
                newest = max(
                    entries,
                    key=lambda item: item.get("published_at") or 0,
                )
                if not feed["initialized"]:
                    await self.db.set_feed_cursor(
                        feed["id"],
                        entry_key=newest["key"],
                        published_at=newest.get("published_at"),
                    )
                    log.info("Лента %s инициализирована без отправки старых публикаций", feed["id"])
                    return

                anchor = next(
                    (index for index, item in enumerate(entries) if item["key"] == feed["last_entry_key"]),
                    None,
                )
                if anchor is not None:
                    candidates = list(reversed(entries[:anchor]))
                else:
                    previous_time = feed["last_entry_published"]
                    newer = [
                        item
                        for item in entries
                        if item.get("published_at") is not None
                        and (previous_time is None or item["published_at"] > previous_time)
                    ]
                    candidates = sorted(newer, key=lambda item: item.get("published_at") or 0)
                    if not candidates and previous_time is None and newest["key"] != feed["last_entry_key"]:
                        candidates = [newest]

                # Keep a large burst from flooding one channel; the cursor moves only as items succeed.
                candidates = candidates[:10]

                for entry in candidates:
                    if await self.db.has_delivery(feed["id"], entry["key"]):
                        await self.db.set_feed_cursor(
                            feed["id"], entry_key=entry["key"], published_at=entry.get("published_at")
                        )
                        continue
                    message = await self.send_entry(feed, entry)
                    await self.db.record_delivery(feed["id"], entry["key"], str(message.id))
                    await self.db.set_feed_cursor(
                        feed["id"], entry_key=entry["key"], published_at=entry.get("published_at")
                    )
                    log.info("Отправлена публикация из ленты %s: %s", feed["id"], entry["title"][:120])

                if not candidates:
                    await self.db.set_feed_cursor(
                        feed["id"], entry_key=newest["key"], published_at=newest.get("published_at")
                    )
            except (FeedFetchError, discord.HTTPException, RuntimeError, OSError) as exc:
                delay = min(3600, max(interval, 120))
                await self.db.set_poll_error(feed["id"], next_poll_at=time.time() + delay, error=str(exc))
                log.warning("Ошибка обработки RSS-ленты %s: %s", feed["id"], exc)
            except Exception as exc:
                delay = min(3600, max(interval, 120))
                await self.db.set_poll_error(feed["id"], next_poll_at=time.time() + delay, error=str(exc))
                log.exception("Неожиданная ошибка обработки RSS-ленты %s", feed["id"])
