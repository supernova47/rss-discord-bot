from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

TEMPLATE_TAGS = {
    "title",
    "url",
    "link",
    "description",
    "content",
    "author",
    "published",
    "feed",
    "image",
    "media",
    "id",
}
TAG_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
TIMESTAMP_STYLES = {
    "relative": ("R",),
    "localized": ("f",),
    "full": ("F",),
    "both": ("R", "f"),
}
LAYOUT_BLOCKS = ("title", "media", "description", "buttons")
SEPARATOR_BLOCK = "separator"
DEFAULT_LAYOUT_ORDER = ",".join(LAYOUT_BLOCKS)


def strip_html(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = HTML_TAG_PATTERN.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def template_tags(template: str) -> set[str]:
    return set(TAG_PATTERN.findall(template or ""))


def render_template(template: str, values: dict[str, str], limit: int = 2000) -> str:
    rendered = TAG_PATTERN.sub(lambda match: values.get(match.group(1), ""), template or "")
    return rendered[:limit].strip()


def discord_timestamp(timestamp: Any, style: str = "both") -> str:
    if timestamp is None or timestamp == "":
        return ""
    try:
        unix_timestamp = int(float(timestamp))
    except (ValueError, TypeError, OverflowError):
        return ""
    styles = TIMESTAMP_STYLES.get(style, TIMESTAMP_STYLES["both"])
    return " · ".join(f"<t:{unix_timestamp}:{item}>" for item in styles)


def parse_layout_order(value: Any) -> list[str]:
    blocks = [item.strip() for item in str(value or "").split(",") if item.strip()]
    content_blocks = [item for item in blocks if item != SEPARATOR_BLOCK]
    separators = [index for index, item in enumerate(blocks) if item == SEPARATOR_BLOCK]
    if (
        len(content_blocks) == len(LAYOUT_BLOCKS)
        and set(content_blocks) == set(LAYOUT_BLOCKS)
        and len(separators) <= len(LAYOUT_BLOCKS)
        and (not blocks or blocks[0] != SEPARATOR_BLOCK)
        and all(index == 0 or blocks[index - 1] != SEPARATOR_BLOCK for index in separators)
    ):
        return blocks
    return list(LAYOUT_BLOCKS)


def parse_link_buttons(value: Any) -> list[dict[str, str]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return []
    if not isinstance(value, list):
        return []
    buttons = []
    for item in value[:5]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        url = str(item.get("url") or "").strip()
        if label and url:
            buttons.append({"label": label[:80], "url": url[:512]})
    return buttons


def entry_values(feed: dict[str, Any], entry: dict[str, Any]) -> dict[str, str]:
    published = ""
    timestamp = entry.get("published_at")
    if timestamp:
        try:
            published = datetime.fromtimestamp(float(timestamp), UTC).strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, TypeError, OSError):
            published = ""

    description = strip_html(entry.get("description", ""))
    link = str(entry.get("url") or "")
    return {
        "title": strip_html(entry.get("title", "")),
        "url": link,
        "link": link,
        "description": description,
        "content": description,
        "author": strip_html(entry.get("author", "")),
        "published": published,
        "feed": strip_html(feed.get("title", "")),
        "image": str(entry.get("image") or ""),
        "media": str(entry.get("media") or entry.get("image") or ""),
        "id": str(entry.get("key") or ""),
    }


def parse_color(value: str) -> int:
    cleaned = str(value or "").strip().removeprefix("#")
    if len(cleaned) != 6:
        raise ValueError("Цвет укажите в формате #5865F2")
    try:
        return int(cleaned, 16)
    except ValueError as exc:
        raise ValueError("Цвет укажите в формате #5865F2") from exc


def color_hex(value: int) -> str:
    return f"#{int(value):06X}"
