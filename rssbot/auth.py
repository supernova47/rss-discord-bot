from __future__ import annotations

import json
import time
from typing import Any

import aiohttp
from cryptography.fernet import Fernet, InvalidToken

from rssbot.config import Settings
from rssbot.db import Database


class OAuthError(Exception):
    pass


class SessionExpired(OAuthError):
    pass


class DiscordOAuth:
    def __init__(self, settings: Settings, db: Database, http: aiohttp.ClientSession) -> None:
        self.settings = settings
        self.db = db
        self.http = http
        self._fernet = Fernet(settings.webhook_encryption_key.encode("ascii"))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise SessionExpired("Сессия больше не действует. Войдите в Discord ещё раз.") from exc

    async def exchange_code(self, code: str) -> dict[str, Any]:
        try:
            async with self.http.post(
                "https://discord.com/api/v10/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.settings.oauth_redirect_uri,
                },
                auth=aiohttp.BasicAuth(self.settings.client_id, self.settings.client_secret),
            ) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise OAuthError(
                        "Discord не подтвердил вход. Проверьте OAuth redirect URL в Developer Portal."
                    )
                return data
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise OAuthError("Не удалось связаться с Discord для входа.") from exc

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        try:
            async with self.http.post(
                "https://discord.com/api/v10/oauth2/token",
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                auth=aiohttp.BasicAuth(self.settings.client_id, self.settings.client_secret),
            ) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise SessionExpired("Срок входа в Discord истёк. Войдите ещё раз.")
                return data
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise OAuthError("Не удалось обновить вход через Discord.") from exc

    async def api_get(self, path: str, access_token: str) -> Any:
        try:
            async with self.http.get(
                f"https://discord.com/api/v10{path}",
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                data = await response.json(content_type=None)
                if response.status == 401:
                    raise SessionExpired("Срок входа в Discord истёк. Войдите ещё раз.")
                if response.status >= 400:
                    raise OAuthError("Discord не вернул данные профиля.")
                return data
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise OAuthError("Не удалось получить данные из Discord.") from exc

    async def current_guilds(self, session: dict[str, Any], *, force: bool = False) -> list[dict[str, Any]]:
        now = time.time()
        try:
            cached = json.loads(session.get("guilds_json") or "[]")
        except (TypeError, json.JSONDecodeError):
            cached = []
        if not force and now - float(session.get("guilds_checked_at") or 0) < 60:
            return cached

        access_token = self.decrypt(session["access_token_encrypted"])
        refresh_token = self.decrypt(session["refresh_token_encrypted"])
        if float(session["oauth_expires_at"]) <= now + 60:
            refreshed = await self.refresh_token(refresh_token)
            access_token = str(refreshed["access_token"])
            refresh_token = str(refreshed.get("refresh_token") or refresh_token)
            expiry = now + int(refreshed.get("expires_in", 604800))
            await self.db.update_session_tokens(
                session["id"], self.encrypt(access_token), self.encrypt(refresh_token), expiry
            )
            session["access_token_encrypted"] = self.encrypt(access_token)
            session["refresh_token_encrypted"] = self.encrypt(refresh_token)
            session["oauth_expires_at"] = expiry

        response = await self.api_get("/users/@me/guilds?limit=200", access_token)
        manageable: list[dict[str, Any]] = []
        for guild in response if isinstance(response, list) else []:
            try:
                permissions = int(guild.get("permissions", "0"))
            except (TypeError, ValueError):
                permissions = 0
            if guild.get("owner") or permissions & (8 | 32):
                manageable.append(
                    {
                        "id": str(guild["id"]),
                        "name": str(guild.get("name") or "Discord-сервер"),
                        "icon": str(guild.get("icon") or ""),
                        "owner": bool(guild.get("owner")),
                        "permissions": str(permissions),
                    }
                )
        await self.db.cache_session_guilds(session["id"], manageable)
        session["guilds_json"] = json.dumps(manageable, ensure_ascii=False)
        session["guilds_checked_at"] = now
        return manageable
