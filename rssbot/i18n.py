from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, pass_context

TRANSLATIONS: dict[str, str] = json.loads(
    Path(__file__).with_name("translations.json").read_text(encoding="utf-8")
)

PREFIX_TRANSLATIONS = {
    prefix: TRANSLATIONS[prefix]
    for prefix in (
        "Последняя ошибка: ",
        "Проверено: ",
        "каждые ",
        "Добавить на ",
        "Тест: ",
        "Неизвестные переменные шаблона: ",
        "Не удалось получить RSS-ленту: ",
        "Ответ сайта не похож на RSS или Atom: ",
        "Боту нужны права ",
    )
}


def translate(message: str, language: str = "ru") -> str:
    """Translate known interface copy while preserving unknown and user-provided text."""
    if language != "en":
        return message
    translated = TRANSLATIONS.get(message)
    if translated is not None:
        return translated
    for prefix, translated_prefix in PREFIX_TRANSLATIONS.items():
        if message.startswith(prefix):
            remainder = message[len(prefix):]
            if prefix == "каждые ":
                remainder = remainder.replace("мин", "min")
            return translated_prefix + remainder
    return message


def _plural(value: int, *, one: str, few: str, many: str) -> str:
    value = abs(value)
    last_two = value % 100
    if 11 <= last_two <= 14:
        return many
    last = value % 10
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many


def count_label(kind: str, count: int, language: str = "ru") -> str:
    """Return the localized noun used beside a dashboard count."""
    if kind == "feed":
        if language == "en":
            return "feed" if count == 1 else "feeds"
        return _plural(count, one="лента", few="ленты", many="лент")
    if kind == "channel":
        if language == "en":
            return "available channel" if count == 1 else "available channels"
        return _plural(count, one="доступный канал", few="доступных канала", many="доступных каналов")
    raise ValueError(f"Unknown count label kind: {kind}")


@pass_context
def _template_translate(context: Any, message: str) -> str:
    return translate(message, str(context.get("language", "ru")))


@pass_context
def _template_count(context: Any, kind: str, count: int) -> str:
    return count_label(kind, count, str(context.get("language", "ru")))


def configure_jinja_environment(environment: Environment) -> None:
    environment.globals["t"] = _template_translate
    environment.globals["count_label"] = _template_count
