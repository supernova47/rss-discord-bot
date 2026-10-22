from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_package_root = Path(__file__).resolve().parent.parent
_default_project_root = _package_root if (_package_root / "pyproject.toml").exists() else Path.cwd()
PROJECT_ROOT = Path(os.getenv("RSSBOT_PROJECT_ROOT", str(_default_project_root))).resolve()
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    client_id: str
    client_secret: str
    app_base_url: str
    session_secret: str
    webhook_encryption_key: str
    database_path: Path
    poll_seconds: int
    default_interval_seconds: int
    dev_guild_id: int | None
    port: int
    telegram_alert_bot_token: str = ""
    telegram_alert_chat_id: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        required = {
            "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN", "").strip(),
            "DISCORD_CLIENT_ID": os.getenv("DISCORD_CLIENT_ID", "").strip(),
            "DISCORD_CLIENT_SECRET": os.getenv("DISCORD_CLIENT_SECRET", "").strip(),
            "SESSION_SECRET": os.getenv("SESSION_SECRET", "").strip(),
            "WEBHOOK_ENCRYPTION_KEY": os.getenv("WEBHOOK_ENCRYPTION_KEY", "").strip(),
        }
        missing = [
            name
            for name, value in required.items()
            if not value or value.startswith("put-") or value.startswith("replace-")
        ]
        if missing:
            raise RuntimeError(
                "Заполните обязательные параметры в rss_discord_bot/.env: " + ", ".join(missing)
            )

        telegram_alert_bot_token = os.getenv("TELEGRAM_ALERT_BOT_TOKEN", "").strip()
        telegram_alert_chat_id = os.getenv("TELEGRAM_ALERT_CHAT_ID", "").strip()
        if bool(telegram_alert_bot_token) != bool(telegram_alert_chat_id):
            raise RuntimeError(
                "Для Telegram-уведомлений заполните TELEGRAM_ALERT_BOT_TOKEN и "
                "TELEGRAM_ALERT_CHAT_ID или оставьте оба поля пустыми."
            )

        base_url = os.getenv("APP_BASE_URL", "http://localhost:8000").strip().rstrip("/")
        database_path = Path(os.getenv("DATABASE_PATH", "data/rssbot.sqlite3"))
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path

        dev_guild = os.getenv("DEV_GUILD_ID", "").strip()
        try:
            return cls(
                bot_token=required["DISCORD_BOT_TOKEN"],
                client_id=required["DISCORD_CLIENT_ID"],
                client_secret=required["DISCORD_CLIENT_SECRET"],
                app_base_url=base_url,
                session_secret=required["SESSION_SECRET"],
                webhook_encryption_key=required["WEBHOOK_ENCRYPTION_KEY"],
                database_path=database_path,
                poll_seconds=max(3, int(os.getenv("POLL_SECONDS", "10"))),
                default_interval_seconds=max(60, int(os.getenv("DEFAULT_INTERVAL_SECONDS", "300"))),
                dev_guild_id=int(dev_guild) if dev_guild else None,
                port=max(1, min(65535, int(os.getenv("PORT", "8000")))),
                telegram_alert_bot_token=telegram_alert_bot_token,
                telegram_alert_chat_id=telegram_alert_chat_id,
            )
        except ValueError as exc:
            raise RuntimeError(f"Некорректный параметр в rss_discord_bot/.env: {exc}") from exc

    @property
    def oauth_redirect_uri(self) -> str:
        return f"{self.app_base_url}/auth/callback"

    @property
    def secure_cookies(self) -> bool:
        return self.app_base_url.lower().startswith("https://")
