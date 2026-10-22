from __future__ import annotations

import logging
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet

from rssbot.runtime import RSSRuntime


class RuntimeLoggingTests(unittest.IsolatedAsyncioTestCase):
    async def test_ready_log_includes_number_of_connected_guilds(self) -> None:
        settings = SimpleNamespace(
            webhook_encryption_key=Fernet.generate_key().decode("ascii"),
            dev_guild_id=None,
        )
        runtime = RSSRuntime(settings, db=object())
        runtime.bot._connection._guilds.update({1: object(), 2: object(), 3: object()})

        with patch.object(runtime.bot.tree, "sync", new=AsyncMock()):
            with self.assertLogs("rssbot", level="INFO") as captured:
                await runtime.bot.on_ready()

        self.assertTrue(any("серверов: 3" in message for message in captured.output))

    def test_configured_log_time_uses_moscow_timezone(self) -> None:
        from rssbot.logging_config import configure_moscow_time

        original_converter = logging.Formatter.converter
        self.addCleanup(setattr, logging.Formatter, "converter", original_converter)
        configure_moscow_time()

        timestamp = datetime(2026, 1, 1, 0, 0, tzinfo=UTC).timestamp()
        record = logging.LogRecord("rssbot", logging.INFO, __file__, 1, "test", (), None)
        record.created = timestamp

        formatted = logging.Formatter("%(asctime)s", datefmt="%Y-%m-%d %H:%M:%S").format(record)

        self.assertEqual("2026-01-01 03:00:00", formatted)


if __name__ == "__main__":
    unittest.main()
