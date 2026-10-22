# Product

## Platform

Web application

## Users

The primary user is a Discord server owner or administrator, including members with the Manage Server permission. They configure RSS and Atom feeds so new posts appear in the right channels without manual reposting. Success means reliable delivery without duplicates and without sending the archive when a feed is first added.

## Product purpose

FeedFlow is a self-hosted Discord bot with a web dashboard. It checks RSS and Atom feeds and posts new entries to selected Discord channels, helping communities keep up with updates.

## Positioning

Administrators sign in with Discord OAuth, choose a server and channel, then configure each feed independently. When a feed is added, FeedFlow stores the current position in the source so older posts are not sent.

## Operating context

The dashboard runs in a browser. The bot and its scheduler must stay running to check feeds. The project supports local development on Windows and self-hosting on a Linux VPS with Docker Compose. SQLite and the feed scheduler support a single application instance.

## Capabilities and constraints

- Discord OAuth2 sign-in and a list of servers the user can manage.
- Create, search, edit, pause, test, and delete RSS and Atom feeds.
- Follow YouTube channels through Atom without a separate YouTube API key. Other websites must expose a public HTTP(S) RSS or Atom feed; pages without a feed are not scraped.
- Configure the target Discord channel, polling interval, message templates and layout, image or media, link buttons, and sender identity for each feed.
- Prevent duplicate deliveries. Do not send the archive when a feed is first added.
- Store settings, sessions, and delivery history in SQLite. Encrypt Discord OAuth and webhook tokens before storing them.
- Validate feed DNS records and redirects, reject private IP addresses, and prevent mass mentions.
- Support one application process only; SQLite and the feed scheduler are not designed for multiple replicas.
- Provide an English and Russian dashboard. Detect the default language from the browser.

## Evidence

The README, application source, and deployment guides document the current capabilities. The project has no verified customer testimonials, case studies, or independent reliability metrics. Do not invent them in future product copy.

## Product principles

- Start new feeds from the current entry and do not post their archives.
- Let administrators choose the destination channel and manage each feed independently.
- Describe source support accurately: FeedFlow supports RSS and Atom, not arbitrary pages without feeds.
- Preserve operator control over data and provide a recovery path using the database and environment secrets.