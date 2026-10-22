(() => {
  // Intl uses the browser's preferred language and local time zone. Keep the
  // server-rendered UTC text as a fallback if localization is unavailable.
  const locale = navigator.languages?.[0] || navigator.language || document.documentElement.lang;
  for (const element of document.querySelectorAll("time.local-datetime[data-unix]")) {
    const timestamp = Number(element.dataset.unix);
    if (!Number.isFinite(timestamp)) continue;
    try {
      element.textContent = new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(timestamp * 1000));
    } catch {
      // Keep the UTC value rendered by the server.
    }
  }

  if (document.documentElement.lang !== "en") return;

  const phrases = {
    "Выйти": "Log out",
    "RSS и Atom → Discord": "RSS and Atom → Discord",
    "Вдохновлено MonitoRSS": "Inspired by MonitoRSS",
    "НОВОСТИ БЕЗ РУЧНОЙ РАССЫЛКИ": "NEWS WITHOUT MANUAL POSTING",
    "Любимые источники.": "Your favorite sources.",
    "В нужном Discord-канале.": "In the right Discord channel.",
    "Добавьте RSS или Atom-ленту, выберите канал и настройте вид публикации. Новости будут приходить сами.": "Add an RSS or Atom feed, choose a channel, and customize its posts. News will arrive automatically.",
    "Войти через Discord": "Log in with Discord",
    "Добавить бота": "Add bot",
    "Панель доступна владельцам сервера и участникам с правом Manage Server.": "The dashboard is available to server owners and members with Manage Server permission.",
    "НОВАЯ ПУБЛИКАЦИЯ": "NEW POST",
    "сейчас": "now",
    "Читать новость ↗": "Read article ↗",
    "Настройте один раз": "Set it up once",
    "Добавляйте несколько лент и направляйте каждую в свой канал.": "Add multiple feeds and send each one to its own channel.",
    "Оформите по-своему": "Make it your own",
    "Markdown-шаблоны, embed-карточки, цвет, имя и аватар отправителя.": "Markdown templates, embeds, color, sender name, and avatar.",
    "Начните с чистого листа": "Start fresh",
    "После добавления бот запоминает последнюю запись и не засыпает старой историей.": "After setup, the bot saves the latest entry and does not flood the channel with old posts.",
    "ПАНЕЛЬ УПРАВЛЕНИЯ": "DASHBOARD",
    "Ваши Discord-серверы": "Your Discord servers",
    "Выберите сервер, чтобы настроить RSS-ленты.": "Choose a server to configure its RSS feeds.",
    "Добавить бота на сервер": "Add bot to a server",
    "Сессия истекла. Войдите снова.": "Your session expired. Please log in again.",
    "Бот подключается к Discord. Список каналов появится через несколько секунд.": "The bot is connecting to Discord. Channels will appear in a few seconds.",
    "Бот добавлен": "Bot added",
    "Нужно добавить": "Install bot",
    "Открыть панель": "Open dashboard",
    "Добавить бота": "Add bot",
    "Серверы пока не найдены": "No servers found yet",
    "Убедитесь, что у вас есть права владельца, администратора или Manage Server.": "Make sure you are the owner, an administrator, or have Manage Server permission.",
    "Обновить доступ Discord": "Refresh Discord access",
    "Серверы": "Servers",
    "НАСТРОЙКИ СЕРВЕРА": "SERVER SETTINGS",
    "Добавить ленту": "Add feed",
    "Добавьте бота на сервер": "Add the bot to your server",
    "После установки вернитесь сюда и выберите канал для публикаций.": "After installing it, return here and choose a channel for posts.",
    "Боту понадобятся права: View Channel, Send Messages, Embed Links и Manage Webhooks.": "The bot needs View Channel, Send Messages, Embed Links, and Manage Webhooks permissions.",
    "Добавить на ": "Add to ",
    "Бот пока подключается. Обновите страницу через несколько секунд.": "The bot is still connecting. Refresh this page in a few seconds.",
    " в настройках": " configured",
    "доступных канал": "available channel",
    "доступных канала": "available channels",
    "доступных каналов": "available channels",
    "стандартный интервал проверки": "default polling interval",
    "5 мин": "5 min",
    "лента": "feed",
    "ленты": "feeds",
    "лент в настройках": "configured feeds",
    "Нет каналов, где боту разрешено просматривать сообщения и управлять вебхуками. Выдайте View Channel и Manage Webhooks в настройках канала.": "There are no channels where the bot can view messages and manage webhooks. Grant View Channel and Manage Webhooks in the channel settings.",
    "Активна": "Active",
    "На паузе": "Paused",
    "каждые ": "every ",
    "Последняя ошибка: ": "Last error: ",
    "Проверяем ленту. Старые публикации отправлены не будут.": "Checking the feed. Older posts will not be sent.",
    "Проверено: ": "Last checked: ",
    "Тест": "Test",
    "Настроить": "Settings",
    "Пауза": "Pause",
    "Включить": "Enable",
    "Удалить": "Delete",
    "Лент пока нет": "No feeds yet",
    "Добавьте первую RSS или Atom-ленту и выберите канал для новостей.": "Add your first RSS or Atom feed and choose a channel for its posts.",
    "Добавить первую ленту": "Add your first feed",
    "ИСТОЧНИК НОВОСТЕЙ": "NEWS SOURCE",
    "Настройки ленты": "Feed settings",
    "Новая лента": "New feed",
    "Добавить RSS-ленту": "Add RSS feed",
    "Публикация сначала запомнит последнюю запись и не станет отправлять старые новости.": "The bot will save the latest entry first and will not send older posts.",
    "Источник и канал": "Source and channel",
    "Куда смотреть и куда публиковать.": "Where to read from and where to post.",
    "Название ленты": "Feed name",
    "Например, Новости проекта": "For example, Project news",
    "Адрес RSS или Atom": "RSS or Atom feed URL",
    "Поддерживаются публичные HTTP- и HTTPS-адреса.": "Public HTTP and HTTPS URLs are supported.",
    "Канал Discord": "Discord channel",
    "Нет каналов с правами View Channel и Manage Webhooks.": "No channels with View Channel and Manage Webhooks permissions.",
    "Проверять каждые": "Check every",
    "минут": "minutes",
    "Минимум 1 минута, максимум 24 часа. Частые запросы могут быть ограничены самим сайтом.": "From 1 minute to 24 hours. The website may limit frequent requests.",
    "Профиль отправителя": "Sender profile",
    "Для сообщений этой ленты будет использоваться вебхук.": "A webhook will send posts for this feed.",
    "Имя": "Name",
    "От 2 до 32 символов. Discord запрещает слова Discord и Clyde в имени вебхука.": "Use 2–32 characters. Discord does not allow Discord or Clyde in webhook names.",
    "Ссылка на аватар (необязательно)": "Avatar URL (optional)",
    "Используйте публичную ссылку HTTPS или загрузите изображение ниже.": "Use a public HTTPS URL or upload an image below.",
    "Загрузить изображение": "Upload image",
    "PNG или JPG/JPEG, до 8 МБ. Квадратное изображение от 256 × 256 пикселей будет выглядеть лучше. Загруженный файл имеет приоритет над ссылкой.": "PNG or JPG/JPEG, up to 8 MB. A square image of at least 256 × 256 pixels is recommended. An uploaded file takes priority over the URL.",
    "Убрать загруженный аватар": "Remove uploaded avatar",
    "Текущий аватар": "Current avatar",
    "Формат новости": "Post format",
    "Соберите embed и при необходимости добавьте обычный текст Markdown.": "Build an embed and add an optional Markdown message.",
    "Заголовок embed": "Embed title",
    "Описание embed": "Embed description",
    "Текст сообщения над embed — необязательно": "Message above the embed — optional",
    "Можно использовать Markdown Discord. Чтобы оставить только embed, поле можно не заполнять.": "Discord Markdown is supported. Leave this blank to send only the embed.",
    "Цвет карточки": "Card color",
    "Показывать изображение записи, если оно есть": "Show the post image when available",
    "Изображение берётся из полей RSS/Atom и HTML-описания. Прямые GIF-ссылки сохраняют анимацию; если лента передаёт ролик MP4, Discord может показать его как видео.": "Images are read from RSS/Atom fields and HTML descriptions. Direct GIF links stay animated; if the feed provides an MP4, Discord may display it as a video.",
    "Порядок блоков карточки": "Card block order",
    "Перемещайте блоки стрелками. Добавьте разделитель после нужного блока, затем переместите или удалите его. Пустые блоки и отсутствующие изображения пропускаются.": "Move blocks with the arrows. Add a separator after any block, then move or remove it. Empty blocks and missing images are skipped.",
    "Переместить вверх": "Move up",
    "Переместить вниз": "Move down",
    "Добавить разделитель после блока": "Add separator after this block",
    "Удалить разделитель": "Remove separator",
    "Заголовок": "Headline",
    "Изображение или GIF": "Image or GIF",
    "Описание": "Description",
    "Кнопки-ссылки": "Link buttons",
    "До 5 кнопок. Укажите {url}, чтобы вести на статью, или задайте постоянную ссылку HTTP(S).": "Add up to 5 buttons. Use {url} to link to the article, or enter a fixed HTTP(S) address.",
    "Подпись": "Button label",
    "Ссылка": "Link",
    "Убрать": "Remove",
    "Кнопок пока нет": "No buttons yet.",
    "+ Добавить кнопку-ссылку": "+ Add link button",
    "Для каждой кнопки укажите и подпись, и ссылку": "Enter both a label and a link for each button",
    "В одной карточке можно добавить не более пяти кнопок-ссылок": "You can add up to five link buttons to a card",
    "Подпись кнопки не должна быть длиннее 80 символов": "Button labels must be 80 characters or fewer",
    "Ссылка кнопки не должна быть длиннее 512 символов": "Button links must be 512 characters or fewer",
    "Укажите корректную ссылку HTTP(S) или тег {url}": "Enter a valid HTTP(S) link or the {url} tag",
    "Проверьте порядок блоков карточки": "Check the card block order",
    "Переменные для шаблона": "Template variables",
    "Вставляйте названия в фигурных скобках. Неизвестные переменные будут подсвечены при сохранении.": "Put variable names in braces. Unknown variables are reported when you save.",
    "ПРЕДПРОСМОТР": "PREVIEW",
    "пример новости": "example post",
    "Изображение появится, если оно есть в RSS-ленте": "The image will appear here if the RSS entry has one",
    " · сегодня": " · today",
    "Предпросмотр отображает Markdown и расположение блоков. Фактическая карточка зависит от содержимого RSS.": "The preview renders Markdown and shows the block order. The actual post depends on the RSS entry.",
    "Отмена": "Cancel",
    "Сохранить настройки": "Save settings",
    "ИСТОЧНИК НОВОСТЕЙ": "NEWS SOURCE",
    "Выберите новость для теста": "Choose a post to test",
    "Свежие записи загружены напрямую из RSS. Отправка использует сохранённый формат этой ленты.": "Recent entries were fetched directly from RSS. The saved format for this feed will be used.",
    "Дата публикации не указана": "No publication date provided",
    "Открыть запись ↗": "Open entry ↗",
    "Отправить выбранную новость": "Send selected post",
    "Записи не найдены": "No entries found",
    "Проверьте адрес RSS или попробуйте позже.": "Check the RSS URL or try again later.",
    "Назад": "Back",
    "Назад к лентам": "Back to feeds",
    "Новости": "News",
    "Например: 🔔 Новая запись от {feed}": "For example: 🔔 New post from {feed}",
    "{description}\n\n[Читать новость]({url})": "{description}\n\n[Read the article]({url})",
    "Удалить RSS-ленту?": "Delete this RSS feed?",
    "СПРАВКА": "GUIDE",
    "Справка по шаблонам": "Template guide",
    "Теги шаблонов публикаций": "Post template tags",
    "Тег — это имя в фигурных скобках. При отправке бот заменяет его значением из выбранной записи RSS.": "A tag is a name inside braces. When posting, the bot replaces it with a value from the selected RSS entry.",
    "Тег": "Tag",
    "Что подставится": "What it inserts",
    "Пример значения": "Example value",
    "Заголовок публикации": "Post title",
    "Ссылка на публикацию": "Post URL",
    "То же значение, что и ": "Same value as ",
    "Краткое описание без HTML-разметки": "Short description with HTML removed",
    "Автор публикации, если указан в RSS": "Post author, when provided by the feed",
    "Дата публикации в UTC": "Publication date in UTC",
    "Название ленты из настроек бота": "Feed name from the bot settings",
    "Ссылка на изображение, включая картинку из HTML-описания RSS": "Image URL, including an image embedded in the RSS description",
    "Ссылка на GIF или видео для отображения в карточке, если RSS её содержит": "GIF or video URL to display in the card, when provided by the feed",
    "Стабильный ID публикации или её ссылка": "Stable post ID or its URL",
    "Стрелками задайте порядок заголовка, изображения или GIF, описания и кнопок. Нажмите «＋» у нужного блока, чтобы вставить разделитель сразу после него. Разделитель можно перемещать стрелками или удалить. Пустые блоки и отсутствующее изображение пропускаются.": "Use the arrows to order the headline, image or GIF, description, and buttons. Click “＋” next to a block to insert a separator after it. Move the separator with the arrows or remove it. Empty blocks and missing images are skipped.",
    "Порядок блоков, разделители и кнопки-ссылки": "Block order, separators, and link buttons",
    "Бот ищет изображение в RSS-полях и HTML-описании записи. Если лента отдаёт MP4 вместо GIF, Discord может показать его как встроенное видео.": "The bot looks for images in RSS fields and the entry's HTML description. If the feed provides MP4 instead of a GIF, Discord may show it as an embedded video.",
    "Пример embed": "Embed example",
    "В поле заголовка укажите:": "For the title field, enter:",
    "В поле описания:": "For the description field:",
    "Если запись содержит описание «В обновлении появились новые функции» и ссылку, бот соберёт embed так:": "If an entry has the description “The update adds new features” and a URL, the bot builds this embed:",
    "Вышла новая версия приложения": "A new app version is available",
    "В обновлении появились новые функции.": "The update adds new features.",
    "Читать на сайте ↗": "Read on the website ↗",
    "Пример обычного сообщения": "Plain message example",
    "В поле «Текст сообщения над embed» можно написать:": "In the “Message above the embed” field, you can enter:",
    "Результат будет выглядеть так:": "The result will look like this:",
    "Если у записи нет значения для тега, он останется пустым. Для ссылок и форматирования можно использовать Markdown Discord.": "If an entry has no value for a tag, the tag becomes empty. You can use Discord Markdown for links and formatting.",
    "Полная справка по тегам и примеры →": "Full tag guide and examples →",
    "{description}\n\n[Читать на сайте]({url})": "{description}\n\n[Read on the website]({url})",
    "🔔 Новая публикация в **{feed}**: {title}": "🔔 New post in **{feed}**: {title}",
    "🔔 Новая публикация в **Новости проекта**: Вышла новая версия приложения": "🔔 New post in **Project news**: A new app version is available",
    "Настройки ленты сохранены": "Feed settings saved",
    "Тестовое сообщение отправлено": "Test post sent",
    "Лента удалена": "Feed deleted",
    "Лента включена": "Feed enabled",
    "Лента поставлена на паузу": "Feed paused",
    "Не удалось подтвердить вход. Попробуйте ещё раз.": "Could not confirm login. Please try again.",
    "Вход через Discord отменён.": "Discord login was cancelled.",
    "Срок входа истёк. Войдите через Discord ещё раз.": "Your login expired. Please log in with Discord again.",
    "Форма устарела. Обновите страницу и повторите.": "This form has expired. Refresh the page and try again.",
    "Название ленты должно содержать от 1 до 100 символов": "Feed name must contain 1–100 characters",
    "Имя отправителя должно содержать от 2 до 32 символов": "Sender name must contain 2–32 characters",
    "Discord не разрешает слова Discord и Clyde в имени вебхука": "Discord and Clyde are not allowed in webhook names",
    "Укажите другое имя отправителя": "Choose a different sender name",
    "Аватар должен быть меньше 8 МБ": "Avatar must be smaller than 8 MB",
    "Поддерживаются изображения PNG и JPG/JPEG": "PNG and JPG/JPEG images are supported",
    "Аватар должен быть доступен по ссылке HTTPS": "Avatar URL must use HTTPS",
    "Интервал проверки должен быть от 1 минуты до 24 часов": "Polling interval must be between 1 minute and 24 hours",
    "Выберите канал из списка доступных текстовых каналов": "Choose an available text channel",
    "Заполните хотя бы один из шаблонов сообщения или embed": "Fill in at least one message or embed template",
    "На одном сервере можно добавить не более 50 лент": "You can add up to 50 feeds per server",
    "В RSS-ленте пока нет записей для тестовой отправки.": "There are no entries in this RSS feed to test yet.",
    "Эта запись уже исчезла из RSS-ленты. Выберите актуальную запись.": "This entry is no longer in the RSS feed. Choose a current entry.",
    "Сначала войдите через Discord": "Log in with Discord first",
    "Нужны права владельца, администратора или Manage Server": "You need to be the owner, an administrator, or have Manage Server permission",
    "Не удалось завершить Discord OAuth": "Could not complete Discord OAuth",
    "Discord не выдал refresh token. Проверьте OAuth2-настройки приложения.": "Discord did not return a refresh token. Check the app's OAuth2 settings.",
    "RSS-лента должна быть доступна по публичному IP-адресу": "The RSS feed must resolve to a public IP address",
    "Локальные адреса нельзя использовать как RSS-ленту": "Local addresses cannot be used as RSS feeds",
    "RSS-лента больше допустимого размера (2 МБ)": "The RSS feed exceeds the 2 MB size limit",
    "Слишком много переадресаций при загрузке RSS-ленты": "Too many redirects while fetching the RSS feed",
    "Сайт ограничил частоту запросов к RSS-ленте (HTTP 429)": "The site rate-limited RSS requests (HTTP 429)",
    "Некорректный адрес RSS-ленты": "Invalid RSS feed URL",
    "Не удалось определить адрес RSS-сервера": "Could not resolve the RSS server address",
    "Не удалось получить RSS-ленту": "Could not fetch the RSS feed",
    "Веб-панель готова": "Web dashboard is ready",
    "Канал недоступен": "Channel unavailable",
    "Лента не найдена": "Feed not found",
  };
  const prefixes = {
    "Последняя ошибка: ": "Last error: ",
    "Проверено: ": "Last checked: ",
    "каждые ": "every ",
    "Добавить на ": "Add to ",
    "Тест: ": "Test: ",
    "Неизвестные переменные шаблона: ": "Unknown template variables: ",
    "Не удалось получить RSS-ленту: ": "Could not fetch RSS feed: ",
    "Ответ сайта не похож на RSS или Atom: ": "The server response is not valid RSS or Atom: ",
    "Боту нужны права ": "The bot needs permissions ",
  };

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const parent = node.parentElement;
    if (!parent || parent.closest(".feed-url, .user-chip, .feed-main h2, .guild-heading-title h1")) continue;
    const original = node.nodeValue || "";
    const trimmed = original.trim();
    if (!trimmed) continue;
    const leading = original.slice(0, original.indexOf(trimmed));
    const trailing = original.slice(original.indexOf(trimmed) + trimmed.length);
    let translated = phrases[trimmed];
    if (!translated) {
      const feedCount = trimmed.match(/^(\d+) (лента|ленты|лент в настройках)$/);
      if (feedCount) {
        const count = Number(feedCount[1]);
        translated = `${count} ${feedCount[2] === "лент в настройках" ? "configured feeds" : count === 1 ? "feed" : "feeds"}`;
      }
    }
    if (!translated) {
      const channelCount = trimmed.match(/^(\d+) доступных канала?$/);
      if (channelCount) translated = `${channelCount[1]} available channels`;
    }
    if (!translated) {
      const prefix = Object.keys(prefixes).find((candidate) => trimmed.startsWith(candidate));
      if (prefix) {
        let remainder = trimmed.slice(prefix.length);
        if (prefix === "каждые ") remainder = remainder.replace(/\bмин\b/g, "min");
        translated = prefixes[prefix] + remainder;
      }
    }
    if (translated) node.nodeValue = leading + translated + trailing;
  }

  for (const element of document.querySelectorAll("input[placeholder], textarea[placeholder], [aria-label], [title]")) {
    for (const attribute of ["placeholder", "aria-label", "title"]) {
      const value = element.getAttribute(attribute);
      if (value && phrases[value]) element.setAttribute(attribute, phrases[value]);
    }
  }
  for (const element of document.querySelectorAll("[onsubmit]")) {
    const value = element.getAttribute("onsubmit") || "";
    if (value.includes("Удалить RSS-ленту?")) {
      element.setAttribute("onsubmit", value.replace("Удалить RSS-ленту?", "Delete this RSS feed?"));
    }
  }
  for (const title of Object.keys(phrases)) {
    if (document.title.includes(title)) document.title = document.title.replace(title, phrases[title]);
  }
})();
