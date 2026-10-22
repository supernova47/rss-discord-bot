from __future__ import annotations

import base64
import logging
import secrets
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

import aiohttp
import discord
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from rssbot.auth import DiscordOAuth, OAuthError, SessionExpired
from rssbot.config import Settings
from rssbot.db import Database
from rssbot.fetcher import FeedFetchError, validate_feed_url
from rssbot.formatting import (
    DEFAULT_LAYOUT_ORDER,
    LAYOUT_BLOCKS,
    SEPARATOR_BLOCK,
    TEMPLATE_TAGS,
    color_hex,
    parse_color,
    parse_layout_order,
    parse_link_buttons,
    template_tags,
)
from rssbot.i18n import configure_jinja_environment
from rssbot.logging_config import configure_moscow_time
from rssbot.runtime import RSSRuntime

configure_moscow_time()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s MSK %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("rssbot.web")
settings = Settings.from_env()
db = Database(settings.database_path)
PACKAGE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
configure_jinja_environment(templates.env)
MAX_AVATAR_BYTES = 8 * 1024 * 1024


def _datetime_utc(value: Any) -> str:
    try:
        return datetime.fromtimestamp(float(value), UTC).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError, OSError):
        return "—"


templates.env.filters["datetime_utc"] = _datetime_utc


def _button_form_rows(labels: list[str], urls: list[str]) -> list[dict[str, str]]:
    return [
        {
            "label": labels[index] if index < len(labels) else "",
            "url": urls[index] if index < len(urls) else "",
        }
        for index in range(max(len(labels), len(urls)))
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.open()
    auth_http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20, connect=8))
    runtime = RSSRuntime(settings, db)
    app.state.db = db
    app.state.runtime = runtime
    app.state.auth_http = auth_http
    app.state.oauth = DiscordOAuth(settings, db, auth_http)
    await runtime.start()
    log.info("Веб-панель готова: %s", settings.app_base_url)
    try:
        yield
    finally:
        await runtime.close()
        await auth_http.close()
        await db.close()


app = FastAPI(title="FeedFlow", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="discord_rss_session",
    max_age=7 * 24 * 60 * 60,
    same_site="lax",
    https_only=settings.secure_cookies,
)
app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")


@app.get("/language/{language}")
async def choose_language(request: Request, language: str):
    if language not in {"ru", "en"}:
        raise HTTPException(status_code=404)
    request.scope["session"]["language"] = language
    referer = request.headers.get("referer", "")
    parsed = urlsplit(referer)
    destination = parsed.path or "/"
    if parsed.netloc and parsed.netloc != request.headers.get("host"):
        destination = "/"
    if not destination.startswith("/") or destination.startswith("//"):
        destination = "/"
    if parsed.query:
        destination += "?" + parsed.query
    return RedirectResponse(destination, status_code=303)


def _csrf(request: Request) -> str:
    session = request.scope["session"]
    if not session.get("csrf_token"):
        session["csrf_token"] = secrets.token_urlsafe(24)
    return str(session["csrf_token"])


@app.get("/feed-avatars/{feed_id}")
async def feed_avatar(feed_id: str):
    feed = await db.get_feed(feed_id)
    data = feed.get("avatar_data") if feed else None
    if not data:
        raise HTTPException(status_code=404)
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    else:
        raise HTTPException(status_code=404)
    return Response(content=data, media_type=mime, headers={"Cache-Control": "no-store"})


def _check_csrf(request: Request, submitted: str) -> None:
    expected = str(request.scope["session"].get("csrf_token", ""))
    if not expected or not secrets.compare_digest(expected, submitted or ""):
        raise HTTPException(status_code=403, detail="Форма устарела. Обновите страницу и повторите.")


def _avatar_url(user_id: str, avatar: str) -> str:
    return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png?size=64" if avatar else ""


def _invite_url(guild_id: str | None = None) -> str:
    permissions = (1 << 10) | (1 << 11) | (1 << 14) | (1 << 29)
    params: dict[str, str] = {
        "client_id": settings.client_id,
        "scope": "bot applications.commands",
        "permissions": str(permissions),
        "integration_type": "0",
    }
    if guild_id:
        params["guild_id"] = str(guild_id)
        params["disable_guild_select"] = "true"
    return "https://discord.com/oauth2/authorize?" + urlencode(params)


async def _current_session(request: Request) -> dict[str, Any] | None:
    session_id = request.scope["session"].get("db_session_id")
    if not session_id:
        return None
    current = await db.get_session(str(session_id))
    if current is None:
        request.scope["session"].clear()
    return current


async def _authorized_guild(request: Request, guild_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    current = await _current_session(request)
    if current is None:
        raise HTTPException(status_code=401, detail="Сначала войдите через Discord")
    try:
        guilds = await request.app.state.oauth.current_guilds(current)
    except SessionExpired:
        await db.delete_session(current["id"])
        request.scope["session"].clear()
        raise HTTPException(
            status_code=401, detail="Срок входа истёк. Войдите через Discord ещё раз."
        ) from None
    except OAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    target = next((guild for guild in guilds if guild["id"] == str(guild_id)), None)
    if target is None:
        raise HTTPException(status_code=403, detail="Нужны права владельца, администратора или Manage Server")
    return current, target


def _require_csrf_form(request: Request, csrf_token: str) -> None:
    _check_csrf(request, csrf_token)


def _render(request: Request, name: str, **context: Any) -> HTMLResponse:
    context.setdefault("csrf_token", _csrf(request))
    context.setdefault("user", None)
    context.setdefault("language", _language(request))
    return templates.TemplateResponse(request=request, name=name, context=context)


def _language(request: Request) -> str:
    selected = request.scope["session"].get("language")
    if selected in {"ru", "en"}:
        return str(selected)
    preferred = request.headers.get("accept-language", "").split(",", 1)[0].split("-", 1)[0]
    return "en" if preferred == "en" else "ru"


def _avatar_data_url(data: bytes | None) -> str:
    if not data:
        return ""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    else:
        return ""
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _feed_avatar_url(feed: dict[str, Any]) -> str:
    if feed.get("avatar_data"):
        return f"/feed-avatars/{feed['id']}"
    return str(feed.get("avatar_url") or "")


async def _read_avatar_upload(upload: UploadFile | None) -> bytes | None:
    if upload is None or not upload.filename:
        return None
    data = await upload.read(MAX_AVATAR_BYTES + 1)
    if len(data) > MAX_AVATAR_BYTES:
        raise ValueError("Аватар должен быть меньше 8 МБ")
    if not (data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff")):
        raise ValueError("Поддерживаются изображения PNG и JPG/JPEG")
    return data


def _icon(guild: dict[str, Any]) -> str:
    if not guild.get("icon"):
        return ""
    return f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png?size=96"


def _form_channels(request: Request, guild_id: int) -> list[discord.TextChannel]:
    runtime: RSSRuntime = request.app.state.runtime
    return runtime.channels_for(guild_id)


async def _load_panel_context(request: Request, guild_id: int) -> tuple[dict[str, Any], dict[str, Any], Any]:
    current, guild_record = await _authorized_guild(request, guild_id)
    runtime: RSSRuntime = request.app.state.runtime
    guild = runtime.installed_guild(guild_id)
    return current, guild_record, guild


@app.get("/healthz")
async def healthz(request: Request) -> dict[str, str]:
    runtime: RSSRuntime = request.app.state.runtime
    return {"status": "ok", "discord": "connected" if runtime.ready else "connecting"}


@app.get("/help/templates")
async def template_help(request: Request):
    return _render(request, "template_help.html")


@app.get("/")
async def home(request: Request):
    current = await _current_session(request)
    if current is None:
        return _render(request, "home.html", invite_url=_invite_url(), guilds=[], logged_in=False)
    try:
        guilds = await request.app.state.oauth.current_guilds(current)
    except SessionExpired:
        await db.delete_session(current["id"])
        request.scope["session"].clear()
        return RedirectResponse("/?login=expired", status_code=303)
    except OAuthError as exc:
        return _render(
            request, "home.html", invite_url=_invite_url(), guilds=[], logged_in=True, error=str(exc)
        )
    runtime: RSSRuntime = request.app.state.runtime
    guilds = [
        {
            **guild,
            "icon_url": _icon(guild),
            "installed": runtime.installed_guild(int(guild["id"])) is not None,
            "dashboard_url": f"/guilds/{guild['id']}",
            "invite_url": _invite_url(guild["id"]),
        }
        for guild in guilds
    ]
    return _render(
        request,
        "home.html",
        invite_url=_invite_url(),
        guilds=guilds,
        logged_in=True,
        user={
            "username": current["username"],
            "avatar_url": _avatar_url(current["user_id"], current["avatar"]),
        },
        bot_ready=runtime.ready,
    )


@app.get("/auth/login")
async def login(request: Request):
    state = secrets.token_urlsafe(32)
    language = _language(request)
    request.scope["session"].clear()
    request.scope["session"]["oauth_state"] = state
    request.scope["session"]["language"] = language
    query = urlencode(
        {
            "client_id": settings.client_id,
            "redirect_uri": settings.oauth_redirect_uri,
            "response_type": "code",
            "scope": "identify guilds",
            "state": state,
            "prompt": "consent",
        }
    )
    return RedirectResponse(f"https://discord.com/oauth2/authorize?{query}", status_code=302)


@app.get("/auth/callback")
async def oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    session_cookie = request.scope["session"]
    language = _language(request)
    expected_state = str(session_cookie.get("oauth_state", ""))
    if error:
        session_cookie.clear()
        session_cookie["language"] = language
        return _render(
            request,
            "home.html",
            invite_url=_invite_url(),
            guilds=[],
            logged_in=False,
            error="Вход через Discord отменён.",
        )
    if not code or not expected_state or not secrets.compare_digest(expected_state, state):
        session_cookie.clear()
        session_cookie["language"] = language
        return _render(
            request,
            "home.html",
            invite_url=_invite_url(),
            guilds=[],
            logged_in=False,
            error="Не удалось подтвердить вход. Попробуйте ещё раз.",
        )
    try:
        oauth = request.app.state.oauth
        token_data = await oauth.exchange_code(code)
        access_token = str(token_data["access_token"])
        refresh_token = str(token_data.get("refresh_token", ""))
        profile = await oauth.api_get("/users/@me", access_token)
        if not refresh_token:
            raise OAuthError("Discord не выдал refresh token. Проверьте OAuth2-настройки приложения.")
        db_session_id = secrets.token_urlsafe(32)
        await db.create_session(
            session_id=db_session_id,
            user_id=str(profile["id"]),
            username=str(profile.get("global_name") or profile.get("username") or "Discord user"),
            avatar=str(profile.get("avatar") or ""),
            access_token_encrypted=oauth.encrypt(access_token),
            refresh_token_encrypted=oauth.encrypt(refresh_token),
            oauth_expires_at=time.time() + int(token_data.get("expires_in", 604800)),
            guilds=[],
        )
        record = await db.get_session(db_session_id)
        if record is not None:
            await oauth.current_guilds(record, force=True)
        session_cookie.clear()
        session_cookie["language"] = language
        session_cookie["db_session_id"] = db_session_id
        session_cookie["csrf_token"] = secrets.token_urlsafe(24)
        return RedirectResponse("/", status_code=303)
    except (OAuthError, KeyError, ValueError) as exc:
        log.warning("Не удалось завершить Discord OAuth: %s", exc)
        session_cookie.clear()
        session_cookie["language"] = language
        return _render(
            request, "home.html", invite_url=_invite_url(), guilds=[], logged_in=False, error=str(exc)
        )


@app.post("/auth/logout")
async def logout(request: Request, csrf_token: str = Form(...)):
    _require_csrf_form(request, csrf_token)
    language = _language(request)
    session_id = request.scope["session"].get("db_session_id")
    if session_id:
        await db.delete_session(str(session_id))
    request.scope["session"].clear()
    request.scope["session"]["language"] = language
    return RedirectResponse("/", status_code=303)


@app.get("/guilds/{guild_id}")
async def guild_dashboard(request: Request, guild_id: int, notice: str = "", error: str = ""):
    try:
        current, guild_record, guild = await _load_panel_context(request, guild_id)
    except HTTPException as exc:
        if exc.status_code == 401:
            return RedirectResponse("/auth/login", status_code=303)
        raise
    runtime: RSSRuntime = request.app.state.runtime
    if guild is None:
        record = {**guild_record, "icon_url": _icon(guild_record), "invite_url": _invite_url(str(guild_id))}
        return _render(
            request,
            "guild.html",
            guild=record,
            installed=False,
            feeds=[],
            channels=[],
            user={
                "username": current["username"],
                "avatar_url": _avatar_url(current["user_id"], current["avatar"]),
            },
            bot_ready=runtime.ready,
            notice=notice,
            error=error,
        )
    feeds = await db.get_feeds_for_guild(guild_id)
    channel_names = {str(channel.id): channel.name for channel in _form_channels(request, guild_id)}
    for feed in feeds:
        feed["channel_name"] = channel_names.get(feed["channel_id"], "Канал недоступен")
        feed["interval_minutes"] = max(1, int(feed["interval_seconds"]) // 60)
        feed["color_hex"] = color_hex(feed["embed_color"])
        feed["avatar_preview_url"] = _feed_avatar_url(feed)
    record = {**guild_record, "icon_url": _icon(guild_record)}
    return _render(
        request,
        "guild.html",
        guild=record,
        installed=True,
        feeds=feeds,
        channels=_form_channels(request, guild_id),
        user={
            "username": current["username"],
            "avatar_url": _avatar_url(current["user_id"], current["avatar"]),
        },
        bot_ready=runtime.ready,
        notice=notice,
        error=error,
    )


@app.get("/guilds/{guild_id}/feeds/new")
async def new_feed_form(request: Request, guild_id: int):
    try:
        current, guild_record, guild = await _load_panel_context(request, guild_id)
    except HTTPException as exc:
        if exc.status_code == 401:
            return RedirectResponse("/auth/login", status_code=303)
        raise
    if guild is None:
        return RedirectResponse(f"/guilds/{guild_id}", status_code=303)
    channels = _form_channels(request, guild_id)
    if not channels:
        return RedirectResponse(
            f"/guilds/{guild_id}?error=Нет+текстовых+каналов+с+правами+View+Channel+и+Manage+Webhooks",
            status_code=303,
        )
    values = {
        "title": "",
        "url": "",
        "channel_id": str(channels[0].id),
        "display_name": "News" if _language(request) == "en" else "Новости",
        "avatar_url": "",
        "avatar_preview_url": "",
        "message_template": "",
        "embed_title_template": "{title}",
        "embed_description_template": (
            "{description}\n\n[Read the article]({url})"
            if _language(request) == "en"
            else "{description}\n\n[Читать новость]({url})"
        ),
        "embed_color_hex": "#5865F2",
        "show_image": True,
        "layout_order": DEFAULT_LAYOUT_ORDER,
        "show_separators": False,
        "buttons": [],
        "timestamp_style": "both",
        "interval_minutes": max(1, settings.default_interval_seconds // 60),
    }
    return _render(
        request,
        "feed_form.html",
        guild={**guild_record, "icon_url": _icon(guild_record)},
        feed=None,
        values=values,
        channels=channels,
        user={
            "username": current["username"],
            "avatar_url": _avatar_url(current["user_id"], current["avatar"]),
        },
        error="",
        placeholder_tags=(
            "{title}, {url}, {description}, {author}, {published}, {feed}, "
            "{image}, {media}, {id}"
        ),
    )


@app.post("/guilds/{guild_id}/feeds/discover")
async def discover_feed(request: Request, guild_id: int, csrf_token: str = Form(...), url: str = Form(...)):
    _require_csrf_form(request, csrf_token)
    try:
        await _authorized_guild(request, guild_id)
    except HTTPException as exc:
        return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code)
    runtime: RSSRuntime = request.app.state.runtime
    if runtime.fetcher is None:
        return JSONResponse(
            {"error": "Бот ещё подключается. Подождите немного и повторите."}, status_code=503
        )
    try:
        candidates = await runtime.fetcher.discover(url)
    except (FeedFetchError, ValueError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"candidates": candidates})


@app.get("/feeds/preview-media")
async def feed_preview_media(request: Request, url: str):
    if len(url) > 4096:
        return Response(status_code=400)
    if await _current_session(request) is None:
        return Response(status_code=401)
    runtime: RSSRuntime = request.app.state.runtime
    if runtime.fetcher is None:
        return Response(status_code=503)
    try:
        body, media_type = await runtime.fetcher.fetch_preview_media(url)
    except (FeedFetchError, ValueError):
        return Response(status_code=404)
    return Response(
        content=body,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/guilds/{guild_id}/feeds/{feed_id}/edit")
async def edit_feed_form(request: Request, guild_id: int, feed_id: str):
    try:
        current, guild_record, guild = await _load_panel_context(request, guild_id)
    except HTTPException as exc:
        if exc.status_code == 401:
            return RedirectResponse("/auth/login", status_code=303)
        raise
    feed = await db.get_feed(feed_id)
    if feed is None or feed["guild_id"] != str(guild_id):
        raise HTTPException(status_code=404, detail="Лента не найдена")
    if guild is None:
        return RedirectResponse(f"/guilds/{guild_id}", status_code=303)
    channels = _form_channels(request, guild_id)
    values = {
        **feed,
        "avatar_preview_url": _feed_avatar_url(feed),
        "embed_color_hex": color_hex(feed["embed_color"]),
        "show_image": bool(feed["show_image"]),
        "layout_order": ",".join(parse_layout_order(feed.get("layout_order"))),
        "show_separators": bool(feed.get("show_separators", False)),
        "buttons": parse_link_buttons(feed.get("buttons_json", "[]")),
        "timestamp_style": feed.get("timestamp_style", "both"),
        "interval_minutes": max(1, int(feed["interval_seconds"]) // 60),
    }
    return _render(
        request,
        "feed_form.html",
        guild={**guild_record, "icon_url": _icon(guild_record)},
        feed=feed,
        values=values,
        channels=channels,
        user={
            "username": current["username"],
            "avatar_url": _avatar_url(current["user_id"], current["avatar"]),
        },
        error="" if channels else "Нет доступных текстовых каналов с разрешением Manage Webhooks.",
        placeholder_tags=(
            "{title}, {url}, {description}, {author}, {published}, {feed}, "
            "{image}, {media}, {id}"
        ),
    )


def _validated_feed_values(
    *,
    guild_id: int,
    channel_id: str,
    title: str,
    url: str,
    display_name: str,
    avatar_url: str,
    message_template: str,
    embed_title_template: str,
    embed_description_template: str,
    embed_color: str,
    show_image: bool,
    layout_order: str,
    show_separators: bool,
    button_labels: list[str],
    button_urls: list[str],
    timestamp_style: str,
    interval_minutes: int,
    channels: list[discord.TextChannel],
) -> dict[str, Any]:
    clean_title = title.strip()
    clean_name = display_name.strip()
    clean_avatar = avatar_url.strip()
    if not clean_title or len(clean_title) > 100:
        raise ValueError("Название ленты должно содержать от 1 до 100 символов")
    if not 2 <= len(clean_name) <= 32:
        raise ValueError("Имя отправителя должно содержать от 2 до 32 символов")
    if any(word in clean_name.casefold() for word in ("discord", "clyde")):
        raise ValueError("Discord не разрешает слова Discord и Clyde в имени вебхука")
    if clean_name.casefold() in {"everyone", "here"} or "@" in clean_name:
        raise ValueError("Укажите другое имя отправителя")
    if clean_avatar:
        parsed_avatar = urlsplit(clean_avatar)
        if parsed_avatar.scheme != "https" or not parsed_avatar.hostname:
            raise ValueError("Аватар должен быть доступен по ссылке HTTPS")
    if not 1 <= interval_minutes <= 1440:
        raise ValueError("Интервал проверки должен быть от 1 минуты до 24 часов")
    layout_items = [item.strip() for item in layout_order.split(",") if item.strip()]
    content_blocks = [item for item in layout_items if item != SEPARATOR_BLOCK]
    separator_indexes = [index for index, item in enumerate(layout_items) if item == SEPARATOR_BLOCK]
    if (
        len(content_blocks) != len(LAYOUT_BLOCKS)
        or set(content_blocks) != set(LAYOUT_BLOCKS)
        or any(item not in {*LAYOUT_BLOCKS, SEPARATOR_BLOCK} for item in layout_items)
        or len(separator_indexes) > len(LAYOUT_BLOCKS)
        or (layout_items and layout_items[0] == SEPARATOR_BLOCK)
        or any(index > 0 and layout_items[index - 1] == SEPARATOR_BLOCK for index in separator_indexes)
    ):
        raise ValueError("Проверьте порядок блоков карточки")
    if timestamp_style not in {"relative", "localized", "full", "both"}:
        raise ValueError("Выберите формат времени из списка")
    if max(len(button_labels), len(button_urls)) > 5:
        raise ValueError("В одной карточке можно добавить не более пяти кнопок-ссылок")
    buttons = []
    for row in _button_form_rows(button_labels, button_urls):
        label = row["label"].strip()
        button_url = row["url"].strip()
        if not label and not button_url:
            continue
        if not label or not button_url:
            raise ValueError("Для каждой кнопки укажите и подпись, и ссылку")
        if len(label) > 80:
            raise ValueError("Подпись кнопки не должна быть длиннее 80 символов")
        if len(button_url) > 512:
            raise ValueError("Ссылка кнопки не должна быть длиннее 512 символов")
        if button_url != "{url}":
            if template_tags(button_url):
                raise ValueError("Для ссылки кнопки доступен только тег {url}")
            try:
                parsed_button_url = urlsplit(button_url)
                _ = parsed_button_url.port
            except ValueError as exc:
                raise ValueError("Укажите корректную ссылку HTTP(S) или тег {url}") from exc
            if (
                parsed_button_url.scheme not in {"http", "https"}
                or not parsed_button_url.hostname
                or parsed_button_url.username
                or parsed_button_url.password
            ):
                raise ValueError("Укажите корректную ссылку HTTP(S) или тег {url}")
        buttons.append({"label": label, "url": button_url})
    selected_channel = next((channel for channel in channels if str(channel.id) == str(channel_id)), None)
    if selected_channel is None:
        raise ValueError("Выберите канал из списка доступных текстовых каналов")
    clean_url = validate_feed_url(url)
    templates_to_check = (message_template, embed_title_template, embed_description_template)
    unknown_tags = set().union(*(template_tags(item) for item in templates_to_check)) - TEMPLATE_TAGS
    if unknown_tags:
        raise ValueError("Неизвестные переменные шаблона: " + ", ".join(sorted(unknown_tags)))
    if not (message_template.strip() or embed_title_template.strip() or embed_description_template.strip()):
        raise ValueError("Заполните хотя бы один из шаблонов сообщения или embed")
    return {
        "guild_id": guild_id,
        "channel_id": selected_channel.id,
        "title": clean_title,
        "url": clean_url,
        "display_name": clean_name,
        "avatar_url": clean_avatar,
        "message_template": message_template.strip(),
        "embed_title_template": embed_title_template.strip(),
        "embed_description_template": embed_description_template.strip(),
        "embed_color": parse_color(embed_color),
        "show_image": show_image,
        "layout_order": ",".join(layout_items),
        "show_separators": False,
        "buttons": buttons,
        "timestamp_style": timestamp_style,
        "interval_seconds": interval_minutes * 60,
    }


async def _save_feed(
    request: Request,
    guild_id: int,
    feed_id: str | None,
    *,
    csrf_token: str,
    title: str,
    url: str,
    channel_id: str,
    display_name: str,
    avatar_url: str,
    message_template: str,
    embed_title_template: str,
    embed_description_template: str,
    embed_color: str,
    show_image: bool,
    layout_order: str,
    show_separators: bool,
    button_labels: list[str],
    button_urls: list[str],
    timestamp_style: str,
    interval_minutes: int,
    avatar_file: UploadFile | None,
    clear_avatar: bool,
):
    _require_csrf_form(request, csrf_token)
    try:
        current, guild_record, guild = await _load_panel_context(request, guild_id)
    except HTTPException as exc:
        if exc.status_code == 401:
            return RedirectResponse("/auth/login", status_code=303)
        raise
    if guild is None:
        return RedirectResponse(f"/guilds/{guild_id}", status_code=303)
    channels = _form_channels(request, guild_id)
    existing_feed = await db.get_feed(feed_id) if feed_id else None
    avatar_preview = (
        _feed_avatar_url(existing_feed)
        if existing_feed
        else ""
    )
    raw_values = {
        "title": title,
        "url": url,
        "channel_id": channel_id,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "avatar_preview_url": avatar_preview,
        "avatar_data": existing_feed.get("avatar_data") if existing_feed else None,
        "message_template": message_template,
        "embed_title_template": embed_title_template,
        "embed_description_template": embed_description_template,
        "embed_color_hex": embed_color,
        "show_image": show_image,
        "layout_order": layout_order,
        "show_separators": show_separators,
        "buttons": _button_form_rows(button_labels, button_urls),
        "timestamp_style": timestamp_style,
        "interval_minutes": interval_minutes,
    }
    try:
        if feed_id is None and await db.count_feeds_for_guild(guild_id) >= 50:
            raise ValueError("На одном сервере можно добавить не более 50 лент")
        values = _validated_feed_values(
            guild_id=guild_id,
            channel_id=channel_id,
            title=title,
            url=url,
            display_name=display_name,
            avatar_url=avatar_url,
            message_template=message_template,
            embed_title_template=embed_title_template,
            embed_description_template=embed_description_template,
            embed_color=embed_color,
            show_image=show_image,
            layout_order=layout_order,
            show_separators=show_separators,
            button_labels=button_labels,
            button_urls=button_urls,
            timestamp_style=timestamp_style,
            interval_minutes=interval_minutes,
            channels=channels,
        )
        uploaded_avatar = await _read_avatar_upload(avatar_file)
        if uploaded_avatar is not None:
            values["avatar_data"] = uploaded_avatar
            values["avatar_url"] = ""
            raw_values["avatar_preview_url"] = _avatar_data_url(uploaded_avatar)
            raw_values["avatar_data"] = uploaded_avatar
        elif clear_avatar:
            values["avatar_data"] = None
            values["avatar_url"] = ""
            raw_values["avatar_preview_url"] = ""
        elif avatar_url.strip():
            values["avatar_data"] = None
            raw_values["avatar_preview_url"] = avatar_url.strip()
        else:
            values["avatar_data"] = existing_feed.get("avatar_data") if existing_feed else None
            raw_values["avatar_preview_url"] = avatar_preview
        runtime: RSSRuntime = request.app.state.runtime
        if feed_id:
            saved = await db.update_feed(feed_id, values)
        else:
            saved = await db.add_feed(values)
        if saved is None:
            raise HTTPException(status_code=404, detail="Лента не найдена")
        try:
            await runtime.ensure_feed_webhook(
                saved,
                update_avatar=uploaded_avatar is not None or clear_avatar or bool(avatar_url.strip()),
            )
        except (RuntimeError, discord.HTTPException):
            if not feed_id:
                await runtime.delete_feed_webhook(str(saved["id"]))
                await db.delete_feed(str(saved["id"]))
            elif existing_feed:
                await db.update_feed(feed_id, existing_feed)
                try:
                    await runtime.ensure_feed_webhook(existing_feed, update_avatar=True)
                except (RuntimeError, discord.HTTPException):
                    log.exception("Не удалось восстановить аватар вебхука ленты %s", feed_id)
            raise
        return RedirectResponse(f"/guilds/{guild_id}?notice=Настройки+ленты+сохранены", status_code=303)
    except (ValueError, FeedFetchError, RuntimeError, discord.HTTPException) as exc:
        context = {
            "guild": {**guild_record, "icon_url": _icon(guild_record)},
            "feed": existing_feed,
            "values": raw_values,
            "channels": channels,
            "user": {
                "username": current["username"],
                "avatar_url": _avatar_url(current["user_id"], current["avatar"]),
            },
            "error": str(exc),
            "placeholder_tags": (
                "{title}, {url}, {description}, {author}, {published}, {feed}, "
                "{image}, {media}, {id}"
            ),
        }
        return _render(request, "feed_form.html", **context)


@app.post("/guilds/{guild_id}/feeds/new")
async def create_feed(
    request: Request,
    guild_id: int,
    csrf_token: str = Form(...),
    title: str = Form(...),
    url: str = Form(...),
    channel_id: str = Form(...),
    display_name: str = Form("Новости"),
    avatar_url: str = Form(""),
    message_template: str = Form(""),
    embed_title_template: str = Form("{title}"),
    embed_description_template: str = Form("{description}\n\n[Читать новость]({url})"),
    embed_color: str = Form("#5865F2"),
    show_image: bool = Form(False),
    layout_order: str = Form(DEFAULT_LAYOUT_ORDER),
    show_separators: bool = Form(False),
    button_labels: list[str] = Form(default=[]),
    button_urls: list[str] = Form(default=[]),
    timestamp_style: str = Form("both"),
    interval_minutes: int = Form(5),
    avatar_file: UploadFile | None = File(None),
    clear_avatar: bool = Form(False),
):
    return await _save_feed(
        request,
        guild_id,
        None,
        csrf_token=csrf_token,
        title=title,
        url=url,
        channel_id=channel_id,
        display_name=display_name,
        avatar_url=avatar_url,
        message_template=message_template,
        embed_title_template=embed_title_template,
        embed_description_template=embed_description_template,
        embed_color=embed_color,
        show_image=show_image,
        layout_order=layout_order,
        show_separators=show_separators,
        button_labels=button_labels,
        button_urls=button_urls,
        timestamp_style=timestamp_style,
        interval_minutes=interval_minutes,
        avatar_file=avatar_file,
        clear_avatar=clear_avatar,
    )


@app.post("/guilds/{guild_id}/feeds/{feed_id}/edit")
async def update_feed(
    request: Request,
    guild_id: int,
    feed_id: str,
    csrf_token: str = Form(...),
    title: str = Form(...),
    url: str = Form(...),
    channel_id: str = Form(...),
    display_name: str = Form("Новости"),
    avatar_url: str = Form(""),
    message_template: str = Form(""),
    embed_title_template: str = Form("{title}"),
    embed_description_template: str = Form("{description}\n\n[Читать новость]({url})"),
    embed_color: str = Form("#5865F2"),
    show_image: bool = Form(False),
    layout_order: str = Form(DEFAULT_LAYOUT_ORDER),
    show_separators: bool = Form(False),
    button_labels: list[str] = Form(default=[]),
    button_urls: list[str] = Form(default=[]),
    timestamp_style: str = Form("both"),
    interval_minutes: int = Form(5),
    avatar_file: UploadFile | None = File(None),
    clear_avatar: bool = Form(False),
):
    try:
        await _authorized_guild(request, guild_id)
    except HTTPException as exc:
        if exc.status_code == 401:
            return RedirectResponse("/auth/login", status_code=303)
        raise
    feed = await db.get_feed(feed_id)
    if feed is None or feed["guild_id"] != str(guild_id):
        raise HTTPException(status_code=404, detail="Лента не найдена")
    return await _save_feed(
        request,
        guild_id,
        feed_id,
        csrf_token=csrf_token,
        title=title,
        url=url,
        channel_id=channel_id,
        display_name=display_name,
        avatar_url=avatar_url,
        message_template=message_template,
        embed_title_template=embed_title_template,
        embed_description_template=embed_description_template,
        embed_color=embed_color,
        show_image=show_image,
        layout_order=layout_order,
        show_separators=show_separators,
        button_labels=button_labels,
        button_urls=button_urls,
        timestamp_style=timestamp_style,
        interval_minutes=interval_minutes,
        avatar_file=avatar_file,
        clear_avatar=clear_avatar,
    )


async def _feed_action_context(request: Request, guild_id: int, feed_id: str):
    try:
        current, guild_record, guild = await _load_panel_context(request, guild_id)
    except HTTPException as exc:
        if exc.status_code == 401:
            return None, RedirectResponse("/auth/login", status_code=303)
        raise
    feed = await db.get_feed(feed_id)
    if feed is None or feed["guild_id"] != str(guild_id):
        raise HTTPException(status_code=404, detail="Лента не найдена")
    return (current, guild_record, guild, feed), None


@app.post("/guilds/{guild_id}/feeds/{feed_id}/toggle")
async def toggle_feed(request: Request, guild_id: int, feed_id: str, csrf_token: str = Form(...)):
    _require_csrf_form(request, csrf_token)
    context, redirect = await _feed_action_context(request, guild_id, feed_id)
    if redirect:
        return redirect
    _, _, _, feed = context
    updated = await db.toggle_feed(feed_id)
    state = "включена" if updated and updated["is_active"] else "поставлена+на+паузу"
    return RedirectResponse(f"/guilds/{guild_id}?notice=Лента+{state}", status_code=303)


@app.post("/guilds/{guild_id}/feeds/{feed_id}/delete")
async def delete_feed(request: Request, guild_id: int, feed_id: str, csrf_token: str = Form(...)):
    _require_csrf_form(request, csrf_token)
    context, redirect = await _feed_action_context(request, guild_id, feed_id)
    if redirect:
        return redirect
    runtime: RSSRuntime = request.app.state.runtime
    await runtime.delete_feed_webhook(feed_id)
    await db.delete_feed(feed_id)
    return RedirectResponse(f"/guilds/{guild_id}?notice=Лента+удалена", status_code=303)


@app.get("/guilds/{guild_id}/feeds/{feed_id}/test")
async def test_feed_picker(request: Request, guild_id: int, feed_id: str):
    context, redirect = await _feed_action_context(request, guild_id, feed_id)
    if redirect:
        return redirect
    current, guild_record, _, feed = context
    runtime: RSSRuntime = request.app.state.runtime
    error = request.query_params.get("error", "")
    try:
        entries = await runtime.fetch_test_entries(feed)
        if not entries and not error:
            error = "В RSS-ленте пока нет записей для тестовой отправки."
    except (FeedFetchError, RuntimeError) as exc:
        entries = []
        error = str(exc)
    feed["avatar_preview_url"] = _feed_avatar_url(feed)
    return _render(
        request,
        "test_select.html",
        guild={**guild_record, "icon_url": _icon(guild_record)},
        feed=feed,
        entries=entries,
        error=error,
        user={
            "username": current["username"],
            "avatar_url": _avatar_url(current["user_id"], current["avatar"]),
        },
    )


@app.post("/guilds/{guild_id}/feeds/{feed_id}/test")
async def test_feed(
    request: Request,
    guild_id: int,
    feed_id: str,
    csrf_token: str = Form(...),
    entry_key: str = Form(...),
):
    _require_csrf_form(request, csrf_token)
    context, redirect = await _feed_action_context(request, guild_id, feed_id)
    if redirect:
        return redirect
    _, _, _, feed = context
    runtime: RSSRuntime = request.app.state.runtime
    try:
        entries = await runtime.fetch_test_entries(feed)
        selected = next((item for item in entries if item["key"] == entry_key), None)
        if selected is None:
            return RedirectResponse(
                f"/guilds/{guild_id}/feeds/{feed_id}/test?error="
                + urlencode({"error": "Эта запись уже исчезла из RSS-ленты. Выберите актуальную запись."}),
                status_code=303,
            )
        await runtime.send_test(feed, selected)
    except (FeedFetchError, RuntimeError, discord.HTTPException) as exc:
        message = str(exc)[:160]
        return RedirectResponse(
            f"/guilds/{guild_id}/feeds/{feed_id}/test?"
            + urlencode({"error": "Тест: " + message}),
            status_code=303,
        )
    return RedirectResponse(f"/guilds/{guild_id}?notice=Тестовое+сообщение+отправлено", status_code=303)
