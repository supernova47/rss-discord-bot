from __future__ import annotations

import unittest

from rssbot.fetcher import FeedFetcher, FetchResult


class FeedDiscoveryCandidateTests(unittest.TestCase):
    def test_candidate_includes_a_bounded_latest_entry_preview(self) -> None:
        description = "x" * 1800
        long_url = "https://example.com/" + "a" * 2100
        result = FetchResult(
            entries=[
                {"key": "older", "title": "Older entry", "published_at": 1_700_000_000},
                {
                    "key": "entry-" + "k" * 300,
                    "title": "Latest entry",
                    "url": "https://example.com/latest",
                    "description": description,
                    "author": "a" * 180,
                    "published_at": 1_800_000_000.5,
                    "image": long_url,
                    "media": "https://example.com/latest.gif",
                    "media_type": "image/gif",
                    "private_internal_value": "must not be returned",
                },
            ],
            title="Example feed",
            etag=None,
            last_modified=None,
            feed_format="rss",
        )

        candidate = FeedFetcher._candidate("https://example.com/feed.xml", result)

        self.assertEqual(candidate["entries"], ["Latest entry", "Older entry"])
        preview = candidate["preview_entry"]
        self.assertEqual(preview["title"], "Latest entry")
        self.assertEqual(preview["description"], "x" * 1500)
        self.assertEqual(len(preview["key"]), 256)
        self.assertEqual(len(preview["author"]), 150)
        self.assertEqual(len(preview["image"]), 2048)
        self.assertEqual(preview["published_at"], 1_800_000_000.5)
        self.assertEqual(preview["media_type"], "image/gif")
        self.assertNotIn("private_internal_value", preview)
        self.assertEqual(
            set(preview),
            {"key", "title", "url", "description", "author", "published_at", "image", "media", "media_type"},
        )

    def test_candidate_without_entries_has_no_preview_entry(self) -> None:
        result = FetchResult(entries=[], title="Empty feed", etag=None, last_modified=None, feed_format="rss")

        candidate = FeedFetcher._candidate("https://example.com/feed.xml", result)

        self.assertIsNone(candidate["preview_entry"])

    def test_candidate_replaces_non_finite_preview_timestamp(self) -> None:
        result = FetchResult(
            entries=[{"title": "Entry", "published_at": float("nan")}],
            title="Feed",
            etag=None,
            last_modified=None,
            feed_format="rss",
        )

        candidate = FeedFetcher._candidate("https://example.com/feed.xml", result)

        self.assertIsNone(candidate["preview_entry"]["published_at"])


if __name__ == "__main__":
    unittest.main()
