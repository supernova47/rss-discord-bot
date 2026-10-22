from __future__ import annotations

import unittest
from collections.abc import Coroutine
from typing import Any

from rssbot.fetcher import MAX_PREVIEW_MEDIA_BYTES, FeedFetcher, FeedFetchError


class FakeContent:
    def __init__(self, body: bytes) -> None:
        self.body = body

    async def iter_chunked(self, size: int):
        for offset in range(0, len(self.body), size):
            yield self.body[offset : offset + size]


class FakeResponse:
    def __init__(self, status: int, headers: dict[str, str], body: bytes = b"") -> None:
        self.status = status
        self.headers = headers
        self.content_length = len(body) if body else None
        self.content = FakeContent(body)

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.urls: list[str] = []

    def get(self, url: str, *, allow_redirects: bool):
        self.urls.append(url)
        if allow_redirects:
            raise AssertionError("Preview media requests must handle redirects manually")
        return self.responses.pop(0)


def run_immediate(coroutine: Coroutine[Any, Any, Any]) -> Any:
    try:
        try:
            coroutine.send(None)
        except StopIteration as completed:
            return completed.value
        raise AssertionError("Fake media responses must complete without suspending")
    finally:
        coroutine.close()


class PreviewMediaFetchTests(unittest.TestCase):
    def make_fetcher(self, *responses: FakeResponse) -> tuple[FeedFetcher, FakeSession]:
        fetcher = object.__new__(FeedFetcher)
        session = FakeSession(list(responses))
        fetcher._media_session = session
        return fetcher, session

    def test_fetches_only_supported_media_and_returns_its_type(self) -> None:
        response = FakeResponse(200, {"Content-Type": "image/png; charset=binary"}, b"png")
        fetcher, _ = self.make_fetcher(response)

        body, media_type = run_immediate(fetcher.fetch_preview_media("https://example.com/image.png"))

        self.assertEqual((body, media_type), (b"png", "image/png"))

    def test_rejects_files_over_the_preview_limit(self) -> None:
        fetcher, _ = self.make_fetcher(
            FakeResponse(200, {"Content-Type": "image/png"}, b"x" * (MAX_PREVIEW_MEDIA_BYTES + 1))
        )

        with self.assertRaises(FeedFetchError):
            run_immediate(fetcher.fetch_preview_media("https://example.com/large.png"))

    def test_revalidates_redirects_before_following_them(self) -> None:
        fetcher, session = self.make_fetcher(FakeResponse(302, {"Location": "http://127.0.0.1/private.png"}))

        with self.assertRaises(FeedFetchError):
            run_immediate(fetcher.fetch_preview_media("https://example.com/image.png"))

        self.assertEqual(session.urls, ["https://example.com/image.png"])


if __name__ == "__main__":
    unittest.main()
