# Privacy Policy / Политика конфиденциальности — черновик

Before publishing, replace every placeholder in square brackets and make sure the policy matches the actual deployed service, hosting provider, and contact address. Publish it at a stable public HTTPS URL before using it for App Discovery.

Перед публикацией замените все значения в квадратных скобках и проверьте соответствие реальному хостингу и адресу для связи. Для App Discovery страница должна быть публично доступна по HTTPS.

---

## English

### Privacy Policy for Discord RSS

**Last updated:** [DATE]

Discord RSS (“the App”) fetches RSS and Atom feeds selected by server administrators and posts new feed entries to Discord channels configured by those administrators. The dashboard is operated by **[OPERATOR NAME]**. Contact: **[EMAIL ADDRESS]**. Website: **[PUBLIC HTTPS WEBSITE]**.

### Information processed

- **Discord sign-in information:** Discord user ID, username, avatar reference, and the list of servers and permission information returned by Discord OAuth after the user authorizes the dashboard.
- **OAuth credentials:** access and refresh tokens used to keep the dashboard session working and retrieve the authorized user's server list. The App encrypts these tokens before storing them in its database.
- **Feed and server configuration:** server and channel IDs, feed title and URL, sender display name and avatar URL, any uploaded feed avatar, message templates, layout, link buttons, polling interval, and related settings.
- **Delivery and operation records:** feed-entry identifiers, publication timestamps, delivery timestamps, Discord message IDs, polling status, and error text needed to avoid duplicates and troubleshoot feeds.
- **Webhook credentials:** Discord webhook IDs and tokens required to publish to configured channels. Webhook tokens are encrypted before database storage.

The App does not read or store the message history or message content of your Discord server. It uses Discord server/channel information and permissions needed to configure feeds, and sends posts using Discord webhooks. The dashboard uses the `identify` and `guilds` OAuth scopes.

### How information is used

Information is used to authenticate dashboard users, show servers they can manage, save feed settings, fetch configured RSS/Atom URLs, deliver new posts, prevent duplicate deliveries, and diagnose errors. The App does not sell personal information or use it for advertising.

### Sharing and service providers

Feed content is requested from the RSS/Atom websites configured by server administrators and messages are sent to Discord through Discord's API. The service's hosting provider may process data stored on its infrastructure. The operator does not intentionally disclose account or feed data to other parties except to operate the App, comply with law, protect the service, or respond to a valid legal request.

RSS/Atom URLs may identify the website or publisher selected by a server administrator. Feed contents and linked media are provided by those third-party publishers and are subject to their own terms and privacy practices.

### Storage and retention

The App stores configuration and delivery records while a feed exists so it can keep publishing without duplicates. Deleting a feed removes its feed configuration, delivery history, and feed-specific webhook record from the App's database. OAuth dashboard sessions expire after seven days and can also be removed by logging out. Expired sessions are cleaned up by the service. Database backups, if enabled by the operator, may retain deleted data for the backup rotation period: **[DESCRIBE BACKUP RETENTION OR STATE THAT BACKUPS ARE NOT KEPT]**.

### Security

OAuth and webhook tokens are encrypted before being stored in the database. The operator should use HTTPS for any publicly hosted dashboard, restrict access to environment secrets and database backups, and remove credentials if the service is retired. No method of storage or transmission is completely secure.

### Your choices and requests

You can sign out of the dashboard, pause or delete feeds, and remove the App from a server. For questions or requests about stored personal information, contact **[EMAIL ADDRESS]**. Removing the App from a server does not automatically delete a feed's configuration from the database; use the dashboard to delete feeds or contact the operator.

### Children and changes

The App is a general-purpose Discord utility and is not designed to collect information directly from children. The operator may update this policy; the latest version and its effective date will be posted at **[PUBLIC HTTPS PRIVACY POLICY URL]**.

### Contact

**[OPERATOR NAME]**  
**[EMAIL ADDRESS]**  
**[POSTAL ADDRESS, IF REQUIRED FOR YOUR SERVICE]**

---

## Русский

### Политика конфиденциальности Discord RSS

**Дата обновления:** [ДАТА]

Discord RSS («Приложение») получает записи из RSS- и Atom-лент, выбранных администраторами серверов, и публикует новые записи в настроенные ими каналы Discord. Панелью управляет **[ИМЯ ОПЕРАТОРА]**. Контакт: **[АДРЕС ЭЛЕКТРОННОЙ ПОЧТЫ]**. Сайт: **[ПУБЛИЧНЫЙ HTTPS-АДРЕС САЙТА]**.

### Какие данные обрабатываются

- **Данные входа через Discord:** ID пользователя Discord, имя пользователя, ссылка/идентификатор аватара, список серверов и сведения о разрешениях, которые Discord возвращает после OAuth-разрешения для панели.
- **OAuth-токены:** access и refresh токены, необходимые для работы сессии панели и получения списка доступных пользователю серверов. Перед сохранением Приложение шифрует эти токены.
- **Настройки серверов и лент:** ID сервера и канала, название и адрес ленты, имя и ссылка на аватар отправителя, загруженный аватар ленты, шаблоны, порядок блоков, кнопки-ссылки, интервал проверки и другие настройки публикации.
- **Сведения о доставке и работе:** идентификаторы записей ленты, даты публикации и отправки, ID сообщений Discord, статус проверки и тексты ошибок. Эти данные нужны для защиты от повторной отправки и диагностики.
- **Данные вебхуков:** ID и токены Discord-вебхуков, необходимые для публикации в настроенных каналах. Перед записью в базу токены вебхуков шифруются.

Приложение не читает и не сохраняет историю или содержимое сообщений на Discord-сервере. Оно использует сведения о серверах, каналах и разрешениях, необходимые для настройки лент, и публикует новости через вебхуки Discord. Панель запрашивает OAuth scopes `identify` и `guilds`.

### Как используются данные

Данные нужны для входа в панель, показа серверов, которыми пользователь может управлять, сохранения настроек лент, загрузки выбранных RSS/Atom-адресов, отправки новых записей, предотвращения повторов и диагностики ошибок. Оператор не продаёт персональные данные и не использует их для рекламы.

### Передача данных и поставщики услуг

Приложение запрашивает содержимое у RSS/Atom-сайтов, выбранных администратором, и отправляет публикации в Discord через API Discord. Хостинг-провайдер может обрабатывать данные, размещённые на его инфраструктуре. Оператор не передаёт данные аккаунта или лент другим сторонам, кроме случаев работы Приложения, соблюдения закона, защиты сервиса или исполнения законного требования.

RSS/Atom-адреса могут раскрывать сайт или издателя, выбранного администратором. Содержимое лент и связанные изображения предоставляются сторонними издателями и регулируются их собственными условиями и политиками.

### Хранение и сроки

Настройки ленты и записи о доставке хранятся, пока лента существует, чтобы продолжать рассылку без повторов. Удаление ленты удаляет её настройки, историю доставок и привязанный к ней вебхук из базы Приложения. Сессии панели через OAuth истекают через семь дней; их также можно удалить, выйдя из панели. Истёкшие сессии очищаются сервисом. Резервные копии, если оператор их ведёт, могут временно содержать удалённые данные в течение срока ротации: **[УКАЖИТЕ СРОК ХРАНЕНИЯ РЕЗЕРВНЫХ КОПИЙ ИЛИ НАПИШИТЕ, ЧТО ОНИ НЕ ВЕДУТСЯ]**.

### Безопасность

OAuth-токены и токены вебхуков шифруются перед сохранением в базе. Для публичной панели оператору следует использовать HTTPS, ограничивать доступ к секретам окружения и резервным копиям, а при прекращении работы сервиса отзывать и удалять секреты. Ни один способ хранения или передачи данных не гарантирует абсолютную безопасность.

### Ваши действия и запросы

Вы можете выйти из панели, поставить ленты на паузу или удалить их, а также удалить Приложение с сервера. По вопросам хранения персональных данных напишите **[АДРЕС ЭЛЕКТРОННОЙ ПОЧТЫ]**. Удаление Приложения с сервера само по себе не удаляет настройки лент из базы; удалите ленты в панели или обратитесь к оператору.

### Возраст и изменения политики

Приложение — универсальный инструмент Discord; оно не предназначено для непосредственного сбора данных детей. Оператор может обновлять политику. Актуальная версия и дата её вступления в силу будут опубликованы по адресу **[ПУБЛИЧНЫЙ HTTPS-АДРЕС ПОЛИТИКИ]**.

### Контакты

**[ИМЯ ОПЕРАТОРА]**  
**[АДРЕС ЭЛЕКТРОННОЙ ПОЧТЫ]**  
**[ПОЧТОВЫЙ АДРЕС, ЕСЛИ ОН НУЖЕН ДЛЯ ВАШЕГО СЕРВИСА]**

