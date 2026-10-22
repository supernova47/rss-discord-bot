from __future__ import annotations

import asyncio
import calendar
import hashlib
import html
import ipaddress
import math
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

import aiohttp
import feedparser

from rssbot.formatting import strip_html

MAX_FEED_BYTES = 2 * 1024 * 1024
MAX_DISCOVERY_PAGE_BYTES = 6 * 1024 * 1024
MAX_PREVIEW_MEDIA_BYTES = 8 * 1024 * 1024
MAX_REDIRECTS = 5
PREVIEW_MEDIA_TYPES = {
    "image/avif", "image/gif", "image/jpeg", "image/png", "image/webp",
    "video/mp4", "video/webm",
}


class _EntryImageParser(HTMLParser):
    """Collect image URLs embedded in RSS/Atom entry HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    @staticmethod
    def _srcset(value: str) -> list[str]:
        candidates: list[tuple[float, str]] = []
        for part in value.split(","):
            pieces = part.strip().split()
            if not pieces:
                continue
            score = 0.0
            if len(pieces) > 1:
                descriptor = pieces[1].lower()
                try:
                    if descriptor.endswith("w"):
                        score = float(descriptor[:-1])
                    elif descriptor.endswith("x"):
                        score = float(descriptor[:-1]) * 1000
                except ValueError:
                    pass
            candidates.append((score, pieces[0]))
        return [url for _, url in sorted(candidates, reverse=True)]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): html.unescape(value or "") for key, value in attrs}
        candidates: list[str] = []
        if tag == "img":
            candidates.extend(self._srcset(values.get("data-srcset", "")))
            candidates.extend(self._srcset(values.get("srcset", "")))
            candidates.extend(
                values.get(key, "") for key in ("data-original", "data-lazy-src", "data-src", "src")
            )
        elif tag == "source":
            media_type = values.get("type", "").lower()
            if media_type.startswith("image/"):
                candidates.extend(self._srcset(values.get("srcset", "")))
                candidates.append(values.get("src", ""))
        elif tag == "video":
            candidates.append(values.get("poster", ""))
        elif tag == "meta":
            key = f"{values.get('property', '')} {values.get('name', '')}".lower()
            if "image" in key:
                candidates.append(values.get("content", ""))
        self.urls.extend(candidate for candidate in candidates if candidate)


class _FeedLinkParser(HTMLParser):
    """Collect explicitly advertised RSS and Atom links from an HTML page."""

    FEED_TYPES = {"application/rss+xml", "application/atom+xml", "application/rdf+xml"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        values = {key.lower(): html.unescape(value or "") for key, value in attrs}
        relations = {value.lower() for value in values.get("rel", "").split()}
        media_type = values.get("type", "").split(";", 1)[0].strip().lower()
        href = values.get("href", "").strip()
        if "alternate" not in relations or not href:
            return
        if media_type in self.FEED_TYPES or href.lower().split("?", 1)[0].endswith(
            (".rss", ".atom", ".xml")
        ):
            self.links.append((href, values.get("title", "").strip()))


def _public_media_url(value: Any, base_url: str) -> str:
    candidate = html.unescape(str(value or "")).strip()
    if not candidate or candidate.startswith(("data:", "javascript:")):
        return ""
    try:
        parsed = urlsplit(urljoin(base_url, candidate))
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        if parsed.username or parsed.password:
            return ""
        host = parsed.hostname.rstrip(".").lower()
        if host in {"localhost", "metadata.google.internal"} or host.endswith(
            (".localhost", ".local", ".internal")
        ):
            return ""
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            return ""
        return parsed.geturl()
    except ValueError:
        return ""


def _is_animated_image(url: str, media_type: str = "") -> bool:
    if media_type.split(";", 1)[0].strip().lower() in {"image/gif", "image/webp"}:
        return True
    parsed = urlsplit(url)
    suffix = parsed.path.lower().rsplit(".", 1)[-1] if "." in parsed.path else ""
    formats = {value.lower() for value in parse_qs(parsed.query).get("format", [])}
    return (
        suffix in {"gif", "webp"}
        or bool(formats & {"gif", "webp"})
        or "/format/gif" in parsed.path.lower()
    )


def _is_image_media(url: str, media_type: str = "") -> bool:
    if media_type.split(";", 1)[0].strip().lower().startswith("image/"):
        return True
    parsed = urlsplit(url)
    suffix = parsed.path.lower().rsplit(".", 1)[-1] if "." in parsed.path else ""
    formats = {value.lower() for value in parse_qs(parsed.query).get("format", [])}
    return suffix in {"avif", "bmp", "gif", "jpeg", "jpg", "png", "webp"} or bool(
        formats & {"avif", "bmp", "gif", "jpeg", "jpg", "png", "webp"}
    )


class FeedFetchError(Exception):
    pass


@dataclass(slots=True)
class FetchResult:
    entries: list[dict[str, Any]]
    title: str
    etag: str | None
    last_modified: str | None
    not_modified: bool = False
    feed_format: str = ""


def validate_feed_url(url: str) -> str:
    candidate = (url or "").strip()
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as exc:
        raise FeedFetchError("Некорректный адрес RSS-ленты") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise FeedFetchError("Укажите полный адрес RSS/Atom-ленты, начинающийся с http:// или https://")
    if parsed.username or parsed.password:
        raise FeedFetchError("Адрес ленты не должен содержать логин или пароль")
    if port not in {None, 80, 443}:
        raise FeedFetchError("Поддерживаются только стандартные HTTP- и HTTPS-порты")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith(
        (".localhost", ".local", ".internal")
    ):
        raise FeedFetchError("Локальные адреса нельзя использовать как RSS-ленту")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise FeedFetchError("RSS-лента должна быть доступна по публичному IP-адресу")
    return candidate


class PublicOnlyResolver(aiohttp.abc.AbstractResolver):
    """Resolve public feed hosts while refusing private, local, and special-use IPs."""

    def __init__(self) -> None:
        self._resolver = aiohttp.resolver.DefaultResolver()

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_UNSPEC) -> list[dict[str, Any]]:
        results = await self._resolver.resolve(host, port, family)
        if not results:
            raise OSError("Не удалось определить адрес RSS-сервера")
        for result in results:
            try:
                address = ipaddress.ip_address(result["host"])
            except ValueError as exc:
                raise OSError("RSS-сервер вернул некорректный IP-адрес") from exc
            if not address.is_global:
                raise OSError("Подключение к локальным или служебным адресам запрещено")
        return results

    async def close(self) -> None:
        result = self._resolver.close()
        if asyncio.iscoroutine(result):
            await result


class FeedFetcher:
    def __init__(self) -> None:
        connector = aiohttp.TCPConnector(
            resolver=PublicOnlyResolver(),
            use_dns_cache=False,
            limit=12,
            ttl_dns_cache=0,
        )
        timeout = aiohttp.ClientTimeout(total=25, connect=10, sock_read=15)
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "DiscordRSSBot/0.1 (+https://discord.com/developers)"},
            raise_for_status=False,
        )
        media_connector = aiohttp.TCPConnector(
            resolver=PublicOnlyResolver(),
            use_dns_cache=False,
            limit=4,
            ttl_dns_cache=0,
        )
        self._media_session = aiohttp.ClientSession(
            connector=media_connector,
            timeout=aiohttp.ClientTimeout(total=15, connect=5, sock_read=10),
            headers={"User-Agent": "DiscordRSSBot/0.1 (+https://discord.com/developers)"},
            cookie_jar=aiohttp.DummyCookieJar(),
            raise_for_status=False,
        )

    async def close(self) -> None:
        await asyncio.gather(self._session.close(), self._media_session.close())

    async def fetch_preview_media(self, url: str) -> tuple[bytes, str]:
        """Fetch bounded public image/video data for the authenticated web preview."""
        current_url = validate_feed_url(url)
        for redirect_number in range(MAX_REDIRECTS + 1):
            current_url = validate_feed_url(current_url)
            try:
                async with self._media_session.get(current_url, allow_redirects=False) as response:
                    if response.status in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location or redirect_number == MAX_REDIRECTS:
                            raise FeedFetchError("Слишком много переадресаций для медиа предпросмотра")
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status < 200 or response.status >= 300:
                        raise FeedFetchError("Не удалось загрузить медиа предпросмотра")
                    media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                    if media_type not in PREVIEW_MEDIA_TYPES:
                        raise FeedFetchError("Тип файла не поддерживается в предпросмотре")
                    if (
                        response.content_length is not None
                        and response.content_length > MAX_PREVIEW_MEDIA_BYTES
                    ):
                        raise FeedFetchError("Файл слишком большой для предпросмотра (8 МБ)")
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(32_768):
                        body.extend(chunk)
                        if len(body) > MAX_PREVIEW_MEDIA_BYTES:
                            raise FeedFetchError("Файл слишком большой для предпросмотра (8 МБ)")
                    return bytes(body), media_type
            except FeedFetchError:
                raise
            except (aiohttp.ClientError, TimeoutError, OSError) as exc:
                raise FeedFetchError("Не удалось загрузить медиа предпросмотра") from exc
        raise FeedFetchError("Не удалось загрузить медиа предпросмотра")

    async def fetch(self, url: str, *, etag: str = "", last_modified: str = "") -> FetchResult:
        current_url = validate_feed_url(url)
        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        for redirect_number in range(MAX_REDIRECTS + 1):
            current_url = validate_feed_url(current_url)
            try:
                response_context = self._session.get(current_url, headers=headers, allow_redirects=False)
                async with response_context as response:
                    if response.status in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location or redirect_number == MAX_REDIRECTS:
                            raise FeedFetchError("Слишком много переадресаций при загрузке RSS-ленты")
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status == 304:
                        return FetchResult(
                            [], "", response.headers.get("ETag"), response.headers.get("Last-Modified"), True
                        )
                    if response.status == 429:
                        raise FeedFetchError("Сайт ограничил частоту запросов к RSS-ленте (HTTP 429)")
                    if response.status < 200 or response.status >= 300:
                        raise FeedFetchError(f"Сайт вернул HTTP {response.status} при чтении RSS-ленты")
                    content_length = response.content_length
                    if content_length is not None and content_length > MAX_FEED_BYTES:
                        raise FeedFetchError("RSS-лента больше допустимого размера (2 МБ)")
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(32_768):
                        body.extend(chunk)
                        if len(body) > MAX_FEED_BYTES:
                            raise FeedFetchError("RSS-лента больше допустимого размера (2 МБ)")
                    response_etag = response.headers.get("ETag")
                    response_modified = response.headers.get("Last-Modified")
                    break
            except FeedFetchError:
                raise
            except (aiohttp.ClientError, TimeoutError, OSError) as exc:
                raise FeedFetchError(f"Не удалось получить RSS-ленту: {str(exc)[:180]}") from exc
        else:
            raise FeedFetchError("Не удалось загрузить RSS-ленту")

        parsed = await asyncio.to_thread(feedparser.parse, bytes(body))
        if not parsed.entries and getattr(parsed, "bozo", False):
            detail = str(getattr(parsed, "bozo_exception", "неизвестная ошибка"))[:160]
            raise FeedFetchError(f"Ответ сайта не похож на RSS или Atom: {detail}")

        entries = [self._normalize_entry(item, base_url=current_url) for item in parsed.entries[:100]]
        return FetchResult(
            entries=entries,
            title=strip_html(parsed.feed.get("title", "")),
            etag=response_etag,
            last_modified=response_modified,
            feed_format=str(getattr(parsed, "version", "") or ""),
        )

    async def discover(self, url: str) -> list[dict[str, Any]]:
        """Find valid RSS/Atom feeds at a website URL or YouTube channel URL."""
        clean_url = validate_feed_url(url)
        parsed_url = urlsplit(clean_url)
        host = (parsed_url.hostname or "").lower().rstrip(".")
        if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            channel_id = self._youtube_channel_id(clean_url)
            if not channel_id:
                path_parts = parsed_url.path.strip("/").split("/")
                first_part = path_parts[0] if path_parts else ""
                looks_like_channel = first_part.startswith("@") or (
                    first_part in {"channel", "c", "user"} and len(path_parts) > 1
                )
                if not looks_like_channel:
                    raise FeedFetchError(
                        "Вставьте ссылку именно на YouTube-канал, например youtube.com/@channel, "
                        "или прямой Atom-адрес канала."
                    )
                _, page = await self._fetch_html_page(clean_url)
                channel_id = self._youtube_channel_id_from_page(page)
            if not channel_id:
                raise FeedFetchError(
                    "Не удалось определить ID YouTube-канала. Вставьте ссылку вида /channel/UC… "
                    "или прямой Atom-адрес канала."
                )
            feed_url = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"
            result = await self.fetch(feed_url)
            if not self._is_rss_or_atom(result.feed_format):
                raise FeedFetchError("YouTube не вернул ожидаемую Atom-ленту для этого канала")
            return [self._candidate(feed_url, result, kind="YouTube · Atom")]

        try:
            direct_result = await self.fetch(clean_url)
        except FeedFetchError:
            direct_result = None
        if direct_result and self._is_rss_or_atom(direct_result.feed_format):
            return [self._candidate(clean_url, direct_result)]

        page_url, page = await self._fetch_html_page(clean_url)
        parser = _FeedLinkParser()
        try:
            parser.feed(page)
        except (AssertionError, ValueError):
            pass

        candidates: list[tuple[str, str]] = []
        seen: set[str] = set()
        for href, title in parser.links:
            candidate_url = urljoin(page_url, href)
            if candidate_url not in seen:
                seen.add(candidate_url)
                candidates.append((candidate_url, title))

        # Many publishers use one of these conventional root paths without
        # advertising it in HTML. Keep the fallback short and same-origin.
        origin = f"{urlsplit(page_url).scheme}://{urlsplit(page_url).netloc}"
        for path in ("/feed", "/rss", "/feed.xml", "/atom.xml"):
            candidate_url = origin + path
            if candidate_url not in seen:
                seen.add(candidate_url)
                candidates.append((candidate_url, ""))
        candidates = candidates[:8]

        semaphore = asyncio.Semaphore(4)

        async def check_candidate(candidate_url: str, advertised_title: str) -> dict[str, Any] | None:
            async with semaphore:
                try:
                    validate_feed_url(candidate_url)
                    result = await self.fetch(candidate_url)
                except (FeedFetchError, ValueError):
                    return None
                if not self._is_rss_or_atom(result.feed_format):
                    return None
                candidate = self._candidate(candidate_url, result)
                if advertised_title and not result.title:
                    candidate["title"] = strip_html(advertised_title)[:160]
                return candidate

        tasks = [
            asyncio.create_task(check_candidate(candidate_url, advertised_title))
            for candidate_url, advertised_title in candidates
        ]
        done, pending = await asyncio.wait(tasks, timeout=35)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        checked = await asyncio.gather(*(task for task in tasks if task in done), return_exceptions=True)
        return [candidate for candidate in checked if isinstance(candidate, dict)]

    async def _fetch_html_page(self, url: str) -> tuple[str, str]:
        current_url = validate_feed_url(url)
        request_headers = {"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.2"}
        for redirect_number in range(MAX_REDIRECTS + 1):
            current_url = validate_feed_url(current_url)
            try:
                async with self._session.get(
                    current_url, headers=request_headers, allow_redirects=False
                ) as response:
                    if response.status in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location or redirect_number == MAX_REDIRECTS:
                            raise FeedFetchError("Слишком много переадресаций при поиске RSS/Atom")
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status == 429:
                        raise FeedFetchError("Сайт ограничил частоту запросов (HTTP 429)")
                    if response.status < 200 or response.status >= 300:
                        raise FeedFetchError(f"Сайт вернул HTTP {response.status} при поиске RSS/Atom")
                    if (
                        response.content_length is not None
                        and response.content_length > MAX_DISCOVERY_PAGE_BYTES
                    ):
                        raise FeedFetchError("Страница сайта больше допустимого размера (6 МБ)")
                    body = await response.content.read(MAX_DISCOVERY_PAGE_BYTES + 1)
                    if len(body) > MAX_DISCOVERY_PAGE_BYTES:
                        raise FeedFetchError("Страница сайта больше допустимого размера (6 МБ)")
                    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
                    if content_type and content_type not in {"text/html", "application/xhtml+xml"}:
                        if not body.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                            raise FeedFetchError(
                                "Это не RSS/Atom-лента и не HTML-страница сайта"
                            )
                    charset = response.charset or "utf-8"
                    try:
                        page = body.decode(charset, errors="replace")
                    except LookupError:
                        page = body.decode("utf-8", errors="replace")
                    return current_url, page
            except FeedFetchError:
                raise
            except (aiohttp.ClientError, TimeoutError, OSError) as exc:
                raise FeedFetchError(f"Не удалось открыть страницу сайта: {str(exc)[:160]}") from exc
        raise FeedFetchError("Не удалось открыть страницу сайта")

    @staticmethod
    def _is_rss_or_atom(version: str) -> bool:
        return str(version or "").lower().startswith(("rss", "atom", "rdf"))

    @staticmethod
    def _candidate(url: str, result: FetchResult, *, kind: str | None = None) -> dict[str, Any]:
        entries = sorted(
            result.entries,
            key=lambda entry: entry.get("published_at") or 0,
            reverse=True,
        )[:3]
        title = result.title
        if kind and kind.startswith("YouTube") and entries and entries[0].get("author"):
            title = str(entries[0]["author"])
        preview_entry = None
        if entries:
            entry = entries[0]
            try:
                raw_published_at = entry.get("published_at")
                published_at = float(raw_published_at) if raw_published_at is not None else None
            except (TypeError, ValueError):
                published_at = None
            if published_at is not None and not math.isfinite(published_at):
                published_at = None

            preview_entry = {
                "key": str(entry.get("key") or "")[:256],
                "title": str(entry.get("title") or "Без заголовка")[:300],
                "url": str(entry.get("url") or "")[:2048],
                "description": str(entry.get("description") or "")[:1500],
                "author": str(entry.get("author") or "")[:150],
                "published_at": published_at,
                "image": str(entry.get("image") or "")[:2048],
                "media": str(entry.get("media") or "")[:2048],
                "media_type": str(entry.get("media_type") or "")[:100],
            }
        return {
            "url": url,
            "title": strip_html(title)[:160] or url,
            "kind": kind or ("Atom" if "atom" in result.feed_format.lower() else "RSS/Atom"),
            "entries": [str(entry.get("title") or "Без заголовка")[:180] for entry in entries],
            "preview_entry": preview_entry,
        }

    @staticmethod
    def _youtube_channel_id(url: str) -> str:
        parsed = urlsplit(url)
        query_id = parse_qs(parsed.query).get("channel_id", [""])[0]
        if re.fullmatch(r"UC[a-zA-Z0-9_-]{22}", query_id):
            return query_id
        match = re.search(r"(?:^|/)channel/(UC[a-zA-Z0-9_-]{22})(?:/|$)", parsed.path)
        return match.group(1) if match else ""

    @staticmethod
    def _youtube_channel_id_from_page(page: str) -> str:
        patterns = (
            r'"(?:channelId|externalId)"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"',
            r"/channel/(UC[a-zA-Z0-9_-]{22})",
        )
        for pattern in patterns:
            match = re.search(pattern, page)
            if match:
                return match.group(1)
        return ""

    @staticmethod
    def _normalize_entry(entry: Any, *, base_url: str = "") -> dict[str, Any]:
        title = strip_html(entry.get("title", ""))
        raw_link = str(entry.get("link", "") or "")
        link = _public_media_url(raw_link, base_url) if raw_link else ""
        stable_id = str(entry.get("id") or entry.get("guid") or link).strip()
        published_at: float | None = None
        for field in ("published_parsed", "updated_parsed", "created_parsed"):
            parsed_time = entry.get(field)
            if parsed_time:
                try:
                    published_at = float(calendar.timegm(parsed_time))
                    break
                except (OverflowError, TypeError, ValueError):
                    pass
        if not stable_id:
            stable_id = hashlib.sha256(
                f"{title}\0{link}\0{published_at or ''}".encode("utf-8", errors="replace")
            ).hexdigest()

        summary = entry.get("summary", "")
        if not summary and entry.get("content"):
            summary = entry["content"][0].get("value", "")
        image = ""
        animated_image = ""
        animated_image_type = ""
        video_url = ""
        video_type = ""
        for collection_name in ("media_thumbnail", "media_content", "links"):
            for media in entry.get(collection_name, []) or []:
                raw_media_url = media.get("url") or media.get("href")
                media_url = _public_media_url(raw_media_url, link or base_url)
                media_type = str(media.get("type", "") or "").lower()
                relation = str(media.get("rel", "") or "").lower()
                if not media_url or (collection_name == "links" and relation != "enclosure"):
                    continue
                if _is_image_media(media_url, media_type):
                    if not image:
                        image = media_url
                    if _is_animated_image(media_url, media_type) and not animated_image:
                        animated_image = media_url
                        animated_image_type = media_type or "image/*"
                elif media_type.startswith("video/") and not video_url:
                    video_url = media_url
                    video_type = media_type

        html_blobs: list[str] = []
        for key in ("summary", "description", "content:encoded", "content_encoded"):
            value = entry.get(key)
            if value:
                html_blobs.append(str(value))
        for detail_key in ("summary_detail", "description_detail"):
            detail = entry.get(detail_key)
            if isinstance(detail, dict) and detail.get("value"):
                html_blobs.append(str(detail["value"]))
        for content in entry.get("content", []) or []:
            if isinstance(content, dict) and content.get("value"):
                html_blobs.append(str(content["value"]))

        image_base = link or base_url
        for blob in html_blobs:
            parser = _EntryImageParser()
            try:
                parser.feed(blob)
            except (AssertionError, ValueError):
                continue
            for raw_image_url in parser.urls:
                image_url = _public_media_url(raw_image_url, image_base)
                if not image_url:
                    continue
                if _is_animated_image(image_url):
                    if not animated_image:
                        animated_image = image_url
                        animated_image_type = "image/*"
                    if not image:
                        image = image_url
                elif not image:
                    image = image_url

        media_url = animated_image or video_url or image
        if animated_image:
            media_type = animated_image_type or "image/*"
        elif video_url:
            media_type = video_type
        else:
            media_type = "image/*" if image else ""

        author = entry.get("author", "")
        if not author and entry.get("authors"):
            author = entry["authors"][0].get("name", "")
        return {
            "key": stable_id,
            "title": title or "Без заголовка",
            "url": link,
            "description": strip_html(summary),
            "author": strip_html(author),
            "published_at": published_at,
            "image": image,
            "media": media_url,
            "media_type": media_type,
        }
