# Пакет для Discord Developer Portal

Материалы подготовлены для текущего проекта Discord RSS Bot. Тексты описывают существующие функции: RSS/Atom, веб-панель, отдельную настройку каждой ленты, embed-карточки с изображениями/GIF и ссылками, а также команды `/rss`.

## Предлагаемое имя и короткий слоган

- **Название приложения и бота:** `Discord RSS`
- **Слоган:** `RSS и Atom — прямо в Discord`
- **Альтернативное брендовое имя:** `FeedFlow` (если захочется переименовать приложение; изображения не содержат надписей и подойдут для обоих вариантов).

## Тексты для General Information

### Description — русский

```text
Публикует новости из RSS- и Atom-лент в Discord. Настройте формат, аватар отправителя, время проверки и кнопки отдельно для каждой ленты через панель на русском или английском.
```

### Description — English

```text
Publish RSS and Atom updates in Discord. Customize the layout, sender avatar, polling interval, timestamps, and link buttons for each feed in a Russian- and English-language dashboard.
```

### Текст профиля бота — русский

```text
Новости из RSS и Atom — в нужном канале и в вашем формате. Настройте ленты на веб-панели.
```

### Bot profile text — English

```text
RSS and Atom updates in the channels you choose. Customize every feed in the web dashboard.
```

## App Directory: подробное описание

Раздел Discovery/App Directory может отображаться только у приложения, прошедшего проверку Discord. Сначала сохраните короткое описание в General Information; локализованные тексты ниже понадобятся в Discovery, если этот раздел станет доступен.

### Русский

```text
Discord RSS переносит новые публикации из RSS- и Atom-лент в выбранные каналы сервера.

Добавьте приложение на сервер, войдите в панель через Discord и выберите сервер и канал. Для каждой ленты отдельно задаются адрес RSS/Atom, интервал проверки, имя и аватар отправителя, цвет карточки, шаблоны текста и формат даты. Перетащите блоки в нужном порядке: заголовок, изображение или GIF, описание, кнопки-ссылки и разделители. Для теста можно выбрать реальную запись из ленты.

Приложение публикует новые записи без повторов. При первом добавлении ленты старые публикации не рассылаются. В панели есть русский и английский интерфейс. Команды сервера: /rss list, /rss test и /rss toggle.

Приложение работает с RSS и Atom. Оно не читает историю сообщений сервера: публикации получает из указанных вами лент и отправляет в выбранный канал.
```

### English

```text
Discord RSS delivers new posts from RSS and Atom feeds to the server channels you choose.

Add the app to your server, sign in to the dashboard with Discord, and select a server and channel. Configure each feed independently: its URL, polling interval, sender name and avatar, embed color, text templates, and timestamp style. Arrange the title, image or GIF, description, link buttons, and dividers in the order you want. You can test a feed with a real post selected from its entries.

New posts are delivered without duplicates. Older posts are not sent when a feed is first added. The dashboard supports Russian and English. Server commands: /rss list, /rss test, and /rss toggle.

The app supports RSS and Atom. It does not read server message history; it fetches posts from the feeds you configure and sends them to the selected channel.
```

## Языки и категория

- В **Supported Languages** укажите **Russian** и **English (US)**, если эти варианты доступны в списке. Панель управления приложения локализована на оба языка.
- Категорию выберите ближайшую к **Tools / Utilities / News**, если такие варианты доступны.
- Не отмечайте функции, которых в приложении нет: голосовые функции, модерацию, чтение сообщений или работу с участниками.

## Что загрузить

Файлы лежат в этой же папке:

| Файл | Для чего |
| --- | --- |
| `feedflow-avatar.png` | Иконка приложения в General Information и аватар бота во вкладке Bot. Квадратная, 1254×1254. |
| `feedflow-banner.png` | Широкая обложка для первого изображения в Media Carousel страницы приложения. 2172×724, пропорция 3:1. |
| `feedflow-showcase.png` | Дополнительная иллюстрация Media Carousel с потоком RSS → карточка → Discord. 1672×941. |

Иконку можно обрезать по кругу, поэтому важный знак расположен по центру. Картинки сделаны без текста: название приложения будет чётко отображаться поверх/рядом в Discord и не зависит от выбранного языка.

В текущем интерфейсе Discovery Discord описывает **Media Carousel** (до пяти изображений/видео), а не гарантированное отдельное поле «баннер». Поэтому широкую картинку загружайте как первый элемент карусели, если раздел Discovery доступен. Discord не публикует в просмотренной инструкции точные размеры для этих файлов; размеры выше — фактический размер подготовленных картинок, а не официальная спецификация.

## Пошаговая настройка портала

### 1. General Information

1. Установите имя `Discord RSS` (или выбранное вами имя).
2. Вставьте короткое описание на основном языке приложения.
3. Загрузите `feedflow-avatar.png` как иконку приложения.
4. Сохраните Application ID — он уже используется в локальном `.env` как `DISCORD_CLIENT_ID`; не публикуйте Client Secret.

### 2. Bot

1. Создайте Bot, если он ещё не создан.
2. Поставьте имя `Discord RSS` и тот же `feedflow-avatar.png`.
3. Включите **Public Bot**, чтобы другие владельцы/администраторы могли добавить приложение на свои серверы по ссылке установки.
4. Скопируйте Bot Token в локальный `.env` (`DISCORD_BOT_TOKEN`). Токен не отправляйте в чат, скриншоты, репозиторий или публичную панель.
5. **Privileged Gateway Intents** не включайте. Для текущего RSS-бота они не нужны: он не читает сообщения, не отслеживает участников и статусы.

### 3. Installation

Для **Guild Install** установите scopes:

```text
bot
applications.commands
```

Выберите только эти разрешения бота:

```text
View Channels
Send Messages
Embed Links
Manage Webhooks
```

Они нужны, чтобы бот видел доступные каналы, создавал отдельные webhooks для лент и отправлял оформленные публикации. **Administrator** не требуется. `applications.commands` нужен slash-командам `/rss`; он автоматически входит в scope `bot`, но лучше оставить оба scope в настройке установки как у проекта.

Настройки **User Install** для текущего сценария не нужны: приложение устанавливается на сервер, а веб-панель отдельно входит через OAuth2.

### 4. OAuth2 и вход в панель

В **OAuth2 → Redirects** добавьте точный callback:

```text
http://localhost:8000/auth/callback
```

Для локального запуска `APP_BASE_URL` должен быть `http://localhost:8000`. Панель использует пользовательские OAuth scopes:

```text
identify
guilds
```

`identify` нужен для входа и отображения пользователя; `guilds` — чтобы показать серверы, где пользователь владелец или имеет Manage Server. Сохраните Client ID и Client Secret в `.env` как `DISCORD_CLIENT_ID` и `DISCORD_CLIENT_SECRET`.

Когда панель переедет на хостинг, замените callback на адрес с доменом и HTTPS, например `https://ВАШ-ДОМЕН/auth/callback`. Тот же адрес должен быть задан в `APP_BASE_URL`, а redirect URL должен совпадать с ним в Developer Portal посимвольно. Локальный и production callback можно оставить двумя отдельными разрешёнными адресами.

### 5. Установка на сервер

1. Сохраните изменения портала.
2. Запустите локально `start.bat` и откройте панель на `http://localhost:8000`.
3. Войдите через Discord, добавьте приложение на сервер и выдайте перечисленные разрешения.
4. Настройте ленту. Панель создаёт вебхук в выбранном канале; отдельное имя и аватар задаются для каждой ленты.
5. Команды `/rss list`, `/rss test` и `/rss toggle` доступны участникам с правом Manage Server.

## Открытая установка и публичный каталог — разные вещи

**Public Bot** позволяет другим серверам установить бота по ссылке приглашения. Это не означает автоматическое появление в каталоге Discord. Для страницы в App Directory требуется доступность раздела Discovery, проверка приложения Discord и заполнение обязательных полей. Согласно текущей документации Discord, для включения Discovery также нужны Community support server и опубликованные Privacy Policy и Terms of Service. См. официальные [поля App Directory](https://support-dev.discord.com/hc/en-us/articles/6378525413143-App-Directory-App-profile-pages) и [требования Discovery](https://support-dev.discord.com/hc/en-us/articles/9489299950487-App-Discovery-Content-Requirements-Policy).

Ссылку на локальную панель `localhost` нельзя использовать как публичный сайт или страницу поддержки: она доступна только на вашем компьютере. До публикации приложения замените контакты и ссылки в черновиках политики/условий, разместите эти страницы по публичным HTTPS-адресам и укажите их в портале.

### Поля страницы приложения, когда откроется Discovery

| Поле | Что указать |
| --- | --- |
| Application Description | Подробный текст на русском и английском выше. |
| Support Server | Приглашение на отдельный Discord-сервер поддержки. Сервер должен быть Community. |
| Media Carousel | Сначала `feedflow-banner.png`, затем `feedflow-showcase.png`; позже можно добавить скриншоты реальной панели. Всего до пяти изображений/видео. |
| External Links | Публичный сайт панели, публичный GitHub проекта и руководство пользователя — только если такие страницы доступны. |
| Privacy Policy | Публичный HTTPS URL опубликованной политики из `PRIVACY_POLICY_DRAFT.md`. |
| Terms of Service | Публичный HTTPS URL опубликованных условий из `TERMS_OF_SERVICE_DRAFT.md`. |
| Supported Languages | Russian и English (US), если они есть в списке. |

До выбора хостинга у приложения нет публичного сайта панели: `localhost` виден только на компьютере, где запущен бот. Не вставляйте его в Website, Support Server, Privacy Policy или Terms.

## Ссылка установки для других серверов

В **Installation** удобнее выбрать Discord Provided Link и использовать автоматически созданную ссылку. Если понадобится собрать её вручную, текущий проект использует такие scopes и минимальные разрешения:

```text
https://discord.com/oauth2/authorize?client_id=YOUR_APPLICATION_ID&scope=bot%20applications.commands&permissions=536890368
```

Замените `YOUR_APPLICATION_ID` на Application ID из General Information. Не подставляйте Bot Token или Client Secret в ссылку. На форме Discord пользователь сам выбирает сервер, где имеет право управлять установкой.

## Поля, которые нужно заполнить своими данными

- `ВАШ-ДОМЕН` — публичный HTTPS-домен панели после выбора хостинга.
- `ССЫЛКА-НА-SUPPORT-SERVER` — приглашение в Community-сервер поддержки; для Discovery такой сервер обязателен.
- `EMAIL-ДЛЯ-СВЯЗИ` — адрес для обращений по данным, поддержке и условиям.
- При желании добавьте публичный GitHub-репозиторий, сайт и страницу с инструкцией. Не указывайте приватный репозиторий.

