from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Any

import aiosqlite

from rssbot.formatting import DEFAULT_LAYOUT_ORDER, SEPARATOR_BLOCK, parse_layout_order


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path, timeout=30)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.execute("PRAGMA journal_mode = WAL")
        await self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS feeds (
                id TEXT PRIMARY KEY,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                display_name TEXT NOT NULL,
                avatar_url TEXT NOT NULL DEFAULT '',
                avatar_data BLOB,
                message_template TEXT NOT NULL DEFAULT '',
                embed_title_template TEXT NOT NULL DEFAULT '{title}',
                embed_description_template TEXT NOT NULL DEFAULT '{description}',
                embed_color INTEGER NOT NULL DEFAULT 5793266,
                show_image INTEGER NOT NULL DEFAULT 1,
                image_position TEXT NOT NULL DEFAULT 'after_title',
                layout_order TEXT NOT NULL DEFAULT 'title,media,description,buttons',
                show_separators INTEGER NOT NULL DEFAULT 0,
                buttons_json TEXT NOT NULL DEFAULT '[]',
                timestamp_style TEXT NOT NULL DEFAULT 'both',
                interval_seconds INTEGER NOT NULL DEFAULT 300,
                is_active INTEGER NOT NULL DEFAULT 1,
                initialized INTEGER NOT NULL DEFAULT 0,
                last_entry_key TEXT NOT NULL DEFAULT '',
                last_entry_published REAL,
                etag TEXT NOT NULL DEFAULT '',
                last_modified TEXT NOT NULL DEFAULT '',
                next_poll_at REAL NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                last_success_at REAL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS feeds_due_idx ON feeds(is_active, next_poll_at);
            CREATE INDEX IF NOT EXISTS feeds_guild_idx ON feeds(guild_id, created_at);

            CREATE TABLE IF NOT EXISTS deliveries (
                feed_id TEXT NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
                entry_key TEXT NOT NULL,
                sent_at REAL NOT NULL,
                discord_message_id TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(feed_id, entry_key)
            );

            CREATE TABLE IF NOT EXISTS webhooks (
                channel_id TEXT PRIMARY KEY,
                webhook_id TEXT NOT NULL,
                token_encrypted TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS feed_webhooks (
                feed_id TEXT PRIMARY KEY REFERENCES feeds(id) ON DELETE CASCADE,
                channel_id TEXT NOT NULL,
                webhook_id TEXT NOT NULL,
                token_encrypted TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                avatar TEXT NOT NULL DEFAULT '',
                access_token_encrypted TEXT NOT NULL,
                refresh_token_encrypted TEXT NOT NULL,
                oauth_expires_at REAL NOT NULL,
                guilds_json TEXT NOT NULL DEFAULT '[]',
                guilds_checked_at REAL NOT NULL DEFAULT 0,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_expiry_idx ON sessions(expires_at);
            """
        )
        columns = {
            row["name"]
            for row in await (await self.connection.execute("PRAGMA table_info(feeds)")).fetchall()
        }
        if "avatar_data" not in columns:
            await self.connection.execute("ALTER TABLE feeds ADD COLUMN avatar_data BLOB")
        if "image_position" not in columns:
            await self.connection.execute(
                "ALTER TABLE feeds ADD COLUMN image_position TEXT NOT NULL DEFAULT 'after_title'"
            )
        if "timestamp_style" not in columns:
            await self.connection.execute(
                "ALTER TABLE feeds ADD COLUMN timestamp_style TEXT NOT NULL DEFAULT 'both'"
            )
        if "layout_order" not in columns:
            await self.connection.execute(
                "ALTER TABLE feeds ADD COLUMN layout_order TEXT NOT NULL "
                "DEFAULT 'title,media,description,buttons'"
            )
            legacy_positions = await self._all("SELECT id,image_position FROM feeds")
            for feed in legacy_positions:
                position = feed.get("image_position", "after_title")
                order = {
                    "before_title": "media,title,description,buttons",
                    "after_description": "title,description,media,buttons",
                }.get(position, DEFAULT_LAYOUT_ORDER)
                await self.connection.execute(
                    "UPDATE feeds SET layout_order=? WHERE id=?", (order, feed["id"])
                )
        if "show_separators" not in columns:
            await self.connection.execute(
                "ALTER TABLE feeds ADD COLUMN show_separators INTEGER NOT NULL DEFAULT 0"
            )
        if "buttons_json" not in columns:
            await self.connection.execute(
                "ALTER TABLE feeds ADD COLUMN buttons_json TEXT NOT NULL DEFAULT '[]'"
            )
        legacy_separator_feeds = await self._all(
            "SELECT id,layout_order FROM feeds WHERE show_separators=1"
        )
        for feed in legacy_separator_feeds:
            order = parse_layout_order(feed.get("layout_order"))
            if SEPARATOR_BLOCK not in order:
                separated_order = []
                for block in order:
                    separated_order.extend((block, SEPARATOR_BLOCK))
                order = separated_order
            await self.connection.execute(
                "UPDATE feeds SET layout_order=?, show_separators=0 WHERE id=?",
                (",".join(order), feed["id"]),
            )
        await self.connection.commit()

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()
            self.connection = None

    def _db(self) -> aiosqlite.Connection:
        if self.connection is None:
            raise RuntimeError("Database has not been opened")
        return self.connection

    async def _one(self, query: str, parameters: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        async with self._db().execute(query, parameters) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row is not None else None

    async def _all(self, query: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        async with self._db().execute(query, parameters) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        username: str,
        avatar: str,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        oauth_expires_at: float,
        guilds: list[dict[str, Any]],
        lifetime_seconds: int = 7 * 24 * 60 * 60,
    ) -> None:
        now = time.time()
        await self._db().execute(
            """INSERT INTO sessions (
                id,user_id,username,avatar,access_token_encrypted,refresh_token_encrypted,
                oauth_expires_at,guilds_json,guilds_checked_at,expires_at,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                session_id,
                user_id,
                username,
                avatar,
                access_token_encrypted,
                refresh_token_encrypted,
                oauth_expires_at,
                json.dumps(guilds, ensure_ascii=False),
                now,
                now + lifetime_seconds,
                now,
            ),
        )
        await self._db().commit()

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        return await self._one(
            "SELECT * FROM sessions WHERE id=? AND expires_at>?", (session_id, time.time())
        )

    async def update_session_tokens(
        self,
        session_id: str,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        oauth_expires_at: float,
    ) -> None:
        await self._db().execute(
            """UPDATE sessions SET access_token_encrypted=?, refresh_token_encrypted=?,
               oauth_expires_at=? WHERE id=?""",
            (access_token_encrypted, refresh_token_encrypted, oauth_expires_at, session_id),
        )
        await self._db().commit()

    async def cache_session_guilds(self, session_id: str, guilds: list[dict[str, Any]]) -> None:
        await self._db().execute(
            "UPDATE sessions SET guilds_json=?, guilds_checked_at=? WHERE id=?",
            (json.dumps(guilds, ensure_ascii=False), time.time(), session_id),
        )
        await self._db().commit()

    async def delete_session(self, session_id: str) -> None:
        await self._db().execute("DELETE FROM sessions WHERE id=?", (session_id,))
        await self._db().commit()

    async def delete_expired_sessions(self) -> None:
        await self._db().execute("DELETE FROM sessions WHERE expires_at<=?", (time.time(),))
        await self._db().commit()

    async def get_feeds_for_guild(self, guild_id: int | str) -> list[dict[str, Any]]:
        return await self._all(
            "SELECT * FROM feeds WHERE guild_id=? ORDER BY created_at DESC", (str(guild_id),)
        )

    async def count_feeds_for_guild(self, guild_id: int | str) -> int:
        row = await self._one("SELECT COUNT(*) AS count FROM feeds WHERE guild_id=?", (str(guild_id),))
        return int(row["count"]) if row else 0

    async def get_feed(self, feed_id: str) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM feeds WHERE id=?", (feed_id,))

    async def add_feed(self, values: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        feed_id = secrets.token_hex(6)
        columns = (
            "id,guild_id,channel_id,title,url,display_name,avatar_url,avatar_data,message_template,"
            "embed_title_template,embed_description_template,embed_color,show_image,layout_order,"
            "show_separators,buttons_json,timestamp_style,"
            "interval_seconds,"
            "is_active,initialized,next_poll_at,created_at,updated_at"
        )
        await self._db().execute(
            f"INSERT INTO feeds ({columns}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,0,0,?,?)",
            (
                feed_id,
                str(values["guild_id"]),
                str(values["channel_id"]),
                values["title"],
                values["url"],
                values["display_name"],
                values["avatar_url"],
                values.get("avatar_data"),
                values["message_template"],
                values["embed_title_template"],
                values["embed_description_template"],
                values["embed_color"],
                int(values["show_image"]),
                values.get("layout_order", DEFAULT_LAYOUT_ORDER),
                int(values.get("show_separators", False)),
                json.dumps(values.get("buttons", []), ensure_ascii=False),
                values.get("timestamp_style", "both"),
                values["interval_seconds"],
                now,
                now,
            ),
        )
        await self._db().commit()
        result = await self.get_feed(feed_id)
        if result is None:
            raise RuntimeError("Feed was not saved")
        return result

    async def update_feed(self, feed_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        layout_order = values.get("layout_order", DEFAULT_LAYOUT_ORDER)
        if isinstance(layout_order, (list, tuple)):
            layout_order = ",".join(str(item) for item in layout_order)
        buttons_json = values.get("buttons_json")
        if buttons_json is None:
            buttons_json = json.dumps(values.get("buttons", []), ensure_ascii=False)
        await self._db().execute(
            """UPDATE feeds SET channel_id=?, title=?, url=?, display_name=?, avatar_url=?, avatar_data=?,
               message_template=?, embed_title_template=?, embed_description_template=?, embed_color=?,
               show_image=?, layout_order=?, show_separators=?, buttons_json=?, timestamp_style=?,
               interval_seconds=?, updated_at=? WHERE id=?""",
            (
                str(values["channel_id"]),
                values["title"],
                values["url"],
                values["display_name"],
                values["avatar_url"],
                values.get("avatar_data"),
                values["message_template"],
                values["embed_title_template"],
                values["embed_description_template"],
                values["embed_color"],
                int(values["show_image"]),
                layout_order,
                int(values.get("show_separators", False)),
                buttons_json,
                values.get("timestamp_style", "both"),
                values["interval_seconds"],
                time.time(),
                feed_id,
            ),
        )
        await self._db().commit()
        return await self.get_feed(feed_id)

    async def delete_feed(self, feed_id: str) -> None:
        await self._db().execute("DELETE FROM feeds WHERE id=?", (feed_id,))
        await self._db().commit()

    async def toggle_feed(self, feed_id: str) -> dict[str, Any] | None:
        await self._db().execute(
            "UPDATE feeds SET is_active=CASE is_active WHEN 1 THEN 0 ELSE 1 END, updated_at=? WHERE id=?",
            (time.time(), feed_id),
        )
        await self._db().commit()
        return await self.get_feed(feed_id)

    async def due_feeds(self, now: float | None = None) -> list[dict[str, Any]]:
        return await self._all(
            "SELECT * FROM feeds WHERE is_active=1 AND next_poll_at<=? ORDER BY next_poll_at ASC",
            (now if now is not None else time.time(),),
        )

    async def set_poll_success(
        self,
        feed_id: str,
        *,
        next_poll_at: float,
        etag: str | None,
        last_modified: str | None,
    ) -> None:
        await self._db().execute(
            """UPDATE feeds SET next_poll_at=?, etag=COALESCE(?,etag),
               last_modified=COALESCE(?,last_modified), last_error='', last_success_at=?, updated_at=?
               WHERE id=?""",
            (next_poll_at, etag, last_modified, time.time(), time.time(), feed_id),
        )
        await self._db().commit()

    async def set_poll_error(self, feed_id: str, *, next_poll_at: float, error: str) -> None:
        await self._db().execute(
            "UPDATE feeds SET next_poll_at=?, last_error=?, updated_at=? WHERE id=?",
            (next_poll_at, error[:500], time.time(), feed_id),
        )
        await self._db().commit()

    async def set_feed_cursor(
        self,
        feed_id: str,
        *,
        entry_key: str,
        published_at: float | None,
        initialized: bool = True,
    ) -> None:
        await self._db().execute(
            """UPDATE feeds SET initialized=?, last_entry_key=?,
               last_entry_published=COALESCE(?,last_entry_published), updated_at=? WHERE id=?""",
            (int(initialized), entry_key, published_at, time.time(), feed_id),
        )
        await self._db().commit()

    async def has_delivery(self, feed_id: str, entry_key: str) -> bool:
        row = await self._one(
            "SELECT 1 AS found FROM deliveries WHERE feed_id=? AND entry_key=?", (feed_id, entry_key)
        )
        return row is not None

    async def record_delivery(self, feed_id: str, entry_key: str, message_id: str = "") -> None:
        await self._db().execute(
            "INSERT OR IGNORE INTO deliveries(feed_id,entry_key,sent_at,discord_message_id) VALUES(?,?,?,?)",
            (feed_id, entry_key, time.time(), message_id),
        )
        await self._db().commit()

    async def get_webhook(self, channel_id: int | str) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM webhooks WHERE channel_id=?", (str(channel_id),))

    async def save_webhook(self, channel_id: int | str, webhook_id: int | str, token_encrypted: str) -> None:
        await self._db().execute(
            """INSERT INTO webhooks(channel_id,webhook_id,token_encrypted,created_at)
               VALUES(?,?,?,?) ON CONFLICT(channel_id) DO UPDATE SET
               webhook_id=excluded.webhook_id,token_encrypted=excluded.token_encrypted,
               created_at=excluded.created_at""",
            (str(channel_id), str(webhook_id), token_encrypted, time.time()),
        )
        await self._db().commit()

    async def delete_webhook(self, channel_id: int | str) -> None:
        await self._db().execute("DELETE FROM webhooks WHERE channel_id=?", (str(channel_id),))
        await self._db().commit()

    async def get_feed_webhook(self, feed_id: str) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM feed_webhooks WHERE feed_id=?", (feed_id,))

    async def save_feed_webhook(
        self,
        feed_id: str,
        channel_id: int | str,
        webhook_id: int | str,
        token_encrypted: str,
    ) -> None:
        await self._db().execute(
            """INSERT INTO feed_webhooks(feed_id,channel_id,webhook_id,token_encrypted,created_at)
               VALUES(?,?,?,?,?) ON CONFLICT(feed_id) DO UPDATE SET
               channel_id=excluded.channel_id,webhook_id=excluded.webhook_id,
               token_encrypted=excluded.token_encrypted,created_at=excluded.created_at""",
            (feed_id, str(channel_id), str(webhook_id), token_encrypted, time.time()),
        )
        await self._db().commit()

    async def delete_feed_webhook(self, feed_id: str) -> None:
        await self._db().execute("DELETE FROM feed_webhooks WHERE feed_id=?", (feed_id,))
        await self._db().commit()
