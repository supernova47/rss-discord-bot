# FeedFlow Discord Developer Portal setup

This checklist describes the current FeedFlow application. It covers RSS and Atom feeds, the web dashboard, per-feed post layouts, and the /rss server commands.

## Application name and copy

Use FeedFlow as the application and bot name.

Short description:

~~~text
Publish RSS and Atom updates in Discord. Customize every feed's layout, sender, polling interval, timestamps, and link buttons from the web dashboard.
~~~

Bot profile text:

~~~text
RSS and Atom updates in the channels you choose. Customize every feed in the FeedFlow dashboard.
~~~

Long description for App Directory, if Discord enables Discovery for the application:

~~~text
FeedFlow delivers new posts from RSS and Atom feeds to the Discord channels you choose.

Add FeedFlow to your server, sign in to the dashboard with Discord, and select a server and channel. Configure each feed independently: its URL, polling interval, sender name and avatar, embed color, text templates, and timestamp style. Arrange the title, image or GIF, description, link buttons, and dividers in the order you want. You can test a feed with a real post selected from its entries.

New posts are delivered without duplicates. Older posts are not sent when a feed is first added. The dashboard supports English and Russian. Server commands: /rss list, /rss test, and /rss toggle.

FeedFlow supports RSS and Atom. It does not read server message history; it fetches posts from the feeds you configure and sends them to the selected channel.
~~~

## Installation settings

In General Information:

1. Set the application name to FeedFlow.
2. Paste the short description.
3. Upload feedflow-avatar.png as the application icon.
4. Keep the Application ID private together with the OAuth Client Secret.

In Bot:

1. Create the bot if it does not exist.
2. Set the bot name and avatar to match FeedFlow.
3. Enable Public Bot if other server owners should be able to install it.
4. Store the Bot Token in the server's .env file as DISCORD_BOT_TOKEN. Never share or publish it.
5. Leave Privileged Gateway Intents disabled. FeedFlow does not read messages, monitor members, or track presence.

For Guild Install, use these scopes:

~~~text
bot
applications.commands
~~~

Grant only these bot permissions:

~~~text
View Channels
Send Messages
Embed Links
Manage Webhooks
~~~

Administrator permission is not required. Manage Webhooks is used to create separate webhooks for feeds. User Install is not needed for the current workflow.

## OAuth2 dashboard sign-in

In OAuth2, add the local callback URI:

~~~text
http://localhost:8000/auth/callback
~~~

The dashboard requests these user scopes:

~~~text
identify
guilds
~~~

Store the Application ID and Client Secret in .env as DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET. Set APP_BASE_URL to the exact public HTTPS dashboard URL when deploying the app.

For production, add the matching callback, for example:

~~~text
https://feedflow.example.com/auth/callback
~~~

The callback URL and APP_BASE_URL must match the public domain. You can keep separate local and production redirect URLs in the Developer Portal.

## Start using FeedFlow

1. Save the Developer Portal settings.
2. Start FeedFlow and open the dashboard.
3. Sign in with Discord and install the app on a server where you can manage integrations.
4. Select a channel and configure a feed.
5. Use /rss list, /rss test, and /rss toggle to manage feeds from Discord.

## Public installation and App Directory are separate

Public Bot lets other server owners install the app using its installation link. It does not automatically list the app in Discord's App Directory. Discovery requires Discord review and additional materials. See the official [App Directory profile requirements](https://support-dev.discord.com/hc/en-us/articles/6378525413143-App-Directory-App-profile-pages) and [App Discovery content policy](https://support-dev.discord.com/hc/en-us/articles/9489299950487-App-Discovery-Content-Requirements-Policy).

A localhost dashboard is not a public website or support page. Before applying for Discovery, replace every placeholder in the [Privacy Policy draft](PRIVACY_POLICY_DRAFT.md) and [Terms of Service draft](TERMS_OF_SERVICE_DRAFT.md), publish them at public HTTPS URLs, and add those URLs in the Developer Portal.

## Assets

| File | Purpose |
| --- | --- |
| feedflow-avatar.png | Application icon and bot avatar. Square, 1254 × 1254. |
| feedflow-banner.png | Wide image for the first item in the Discovery Media Carousel. 2172 × 724. |
| feedflow-showcase.png | Additional RSS-to-Discord illustration for the Media Carousel. 1672 × 941. |

Discord may crop the icon into a circle. Important artwork is centered. The images contain no text, so they work with either dashboard language.

The current Discovery interface documents a Media Carousel with up to five images or videos. It does not guarantee a separate banner field. Use feedflow-banner.png as the first carousel item if Discovery is available. The dimensions above are the prepared asset dimensions, not a Discord requirement.

## Installation link

Prefer Discord Provided Link in the Installation section. If you need to assemble a link manually, use the current project scopes and minimal permissions:

~~~text
https://discord.com/oauth2/authorize?client_id=YOUR_APPLICATION_ID&scope=bot%20applications.commands&permissions=536890368
~~~

Replace YOUR_APPLICATION_ID with the Application ID. Never put a Bot Token or Client Secret in an installation link. Discord lets the installer choose a server where they can manage the app.

## Before publishing

- Replace every placeholder in the policy drafts and publish them at public HTTPS URLs.
- Add a real support server and public support contact if required.
- Add the public dashboard URL only after the dashboard is deployed with HTTPS.
- Select English and Russian as supported languages if Discord offers both options.
- Do not claim moderation, voice, message-history, or member-management features; FeedFlow does not provide them.