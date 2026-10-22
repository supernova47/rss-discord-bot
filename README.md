# FeedFlow

[![Latest release](https://img.shields.io/github/v/release/supernova47/rss-discord-bot?label=release)](https://github.com/supernova47/rss-discord-bot/releases/latest)

FeedFlow is a self-hosted Discord bot with a web dashboard. It watches RSS and Atom feeds and posts new entries to the Discord channels you choose.

## Features

- Install the bot on Discord servers with OAuth2.
- Add, edit, search, pause, test, and remove feeds from the web dashboard.
- Discover RSS and Atom feeds from a website URL and preview recent entries before subscribing.
- Follow YouTube channels through their public Atom feeds. No YouTube API key is required.
- Avoid duplicate deliveries. When a feed is added, FeedFlow records its current position instead of posting the archive.
- Customize each post with templates, timestamps, colors, images, GIFs, video, link buttons, and a per-feed sender name and avatar.
- Use the dashboard in English or Russian; its default language follows the browser.
- Optionally receive Telegram alerts when the Discord connection is lost and restored.
- Store settings and delivery history in SQLite. Discord OAuth and webhook tokens are encrypted before they are stored.
- Validate feed DNS records and redirects, reject private IP addresses, limit feed response sizes, and prevent mass mentions.

## Run locally on Windows

### Requirements

- Windows 10 or later
- Python 3.11 or later
- A Discord application with a bot token and OAuth credentials

### Set up Discord

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Add a bot and copy its token.
3. In Installation, enable Guild Install and select the bot and applications.commands scopes. Grant View Channels, Send Messages, Embed Links, and Manage Webhooks. Administrator permission is not required.
4. In OAuth2, add this redirect URI:

   ~~~text
   http://localhost:8000/auth/callback
   ~~~

5. Keep the Application ID and Client Secret private.

For a detailed checklist, see [Discord Developer Portal setup](discord_portal_assets/PORTAL_SETUP.md).

### Configure and start

1. Clone the repository and open its folder in PowerShell:

   ~~~powershell
   git clone https://github.com/supernova47/rss-discord-bot.git
   Set-Location rss-discord-bot
   ~~~

2. Copy .env.example to .env and fill in DISCORD_BOT_TOKEN, DISCORD_CLIENT_ID, and DISCORD_CLIENT_SECRET.
3. Generate the session and encryption keys:

   ~~~powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ~~~

   Put the first value in SESSION_SECRET and the second in WEBHOOK_ENCRYPTION_KEY. Keep the encryption key with your database backups; without it, stored webhook tokens cannot be decrypted.

4. Run start.bat. It creates a virtual environment, installs the application dependencies, and starts the bot and dashboard in the current window.
5. Open [http://localhost:8000](http://localhost:8000), sign in with Discord, add the bot to a server, and configure a feed.

Keep the terminal window open while FeedFlow runs. Press Ctrl+C to stop the bot and dashboard. Only one application instance should use a database at a time.

### Developer checks and package build

Install the development dependencies, run the Python and JavaScript checks, and build the wheel:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test
.\.venv\Scripts\python.exe -m build
~~~

The build command writes package archives to dist/.

To make slash commands appear sooner while testing, set DEV_GUILD_ID to a test server ID. Leave it empty for global registration; Discord may take longer to publish global commands.

## Deploy to a VPS

FeedFlow includes Docker Compose configurations with Caddy for HTTPS and a persistent SQLite volume.

- [General VPS setup, including XorekCloud](deploy/newvps/README.md)
- [Update an existing installation from a GitHub Release](deploy/UPDATE.md)
- [Oracle Cloud deployment](deploy/oracle/README.md)
- [RUVDS deployment](deploy/ruvds/README.md)
- [Selectel deployment](deploy/selectel/README.md)

The deploy/newvps directory name is kept for compatibility with existing installations. The same configuration can be used on a supported Ubuntu or Debian VPS, including the XorekCloud VMmanager panel.

Before exposing the dashboard to the internet, set APP_BASE_URL to its public HTTPS address and add the matching /auth/callback URL to the Discord Developer Portal. Do not expose port 8000 directly; Caddy handles public HTTPS traffic.

## Optional Telegram alerts

Create a separate bot with [@BotFather](https://t.me/BotFather), start a chat with it, and obtain the numeric chat ID. Set TELEGRAM_ALERT_BOT_TOKEN and TELEGRAM_ALERT_CHAT_ID in .env. Leave both values empty to disable alerts. FeedFlow sends one alert for a sustained disconnect and another when the connection is restored.

## Message templates

The feed form can discover RSS or Atom URLs from a website. It supports websites that publish a feed; it does not scrape arbitrary pages without RSS or Atom. For YouTube, paste a channel URL. If discovery cannot resolve it, use a channel URL in the /channel/UC… format or a direct Atom URL.

Available template variables:

| Variable | Description |
| --- | --- |
| <code>{title}</code> | Entry title |
| <code>{url}</code> or <code>{link}</code> | Entry URL |
| <code>{description}</code> or <code>{content}</code> | Plain-text entry description |
| <code>{author}</code> | Entry author |
| <code>{published}</code> | Publication time in UTC |
| <code>{feed}</code> | Feed name shown in the dashboard |
| <code>{image}</code> | Image URL, including images found in the feed's HTML description |
| <code>{media}</code> | GIF or video URL |
| <code>{id}</code> | Stable entry identifier |

For example:

~~~text
Embed title: {title}
Embed description: {description}\n\n[Open the website]({url})
Additional text: New post from **{feed}**
~~~

## Data and security

The default SQLite database path is data/rssbot.sqlite3. Never publish .env, database files, Discord tokens, or encryption keys. Back up the database and WEBHOOK_ENCRYPTION_KEY together. Uploaded feed avatars are stored in SQLite.

The dashboard uses Discord OAuth scopes identify and guilds. Feed publishing uses webhooks created in the selected channels. FeedFlow does not read Discord message history. SQLite and the feed scheduler support a single running application instance.

## Policies and support materials

The Discord Portal folder contains English draft policy documents. Replace every placeholder and review them against the service you operate before publishing:

- [Privacy Policy draft](discord_portal_assets/PRIVACY_POLICY_DRAFT.md)
- [Terms of Service draft](discord_portal_assets/TERMS_OF_SERVICE_DRAFT.md)
- [Discord Developer Portal setup](discord_portal_assets/PORTAL_SETUP.md)

## Releases

See [all FeedFlow releases](https://github.com/supernova47/rss-discord-bot/releases). The release archive contains application and deployment files; it excludes .env, database files, tokens, and local virtual environments.

See the [changelog](CHANGELOG.md) for release history.
