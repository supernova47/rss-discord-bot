from __future__ import annotations

import os

import uvicorn

from rssbot.config import Settings


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run(
        "rssbot.web:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=settings.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
