# Privacy Policy Draft

Before publishing, replace every placeholder and confirm that this policy matches the deployed service, hosting provider, and contact address. Publish it at a stable public HTTPS URL before using it for Discord App Discovery. This draft is not legal advice.

## Privacy Policy for FeedFlow

**Last updated:** [DATE]

FeedFlow (“the App”) fetches RSS and Atom feeds selected by Discord server administrators and posts new feed entries to the channels they configure. The dashboard is operated by **[OPERATOR NAME]**. Contact: **[EMAIL ADDRESS]**. Website: **[PUBLIC HTTPS WEBSITE]**.

## Information processed

- **Discord sign-in information:** Discord user ID, username, avatar reference, and the list of servers and permission information returned by Discord OAuth after the user authorizes the dashboard.
- **OAuth credentials:** Access and refresh tokens used to keep the dashboard session working and retrieve the authorized user's server list. The App encrypts these tokens before storing them in its database.
- **Feed and server configuration:** Server and channel IDs, feed title and URL, sender display name and avatar URL, uploaded feed avatars, message templates, layout, link buttons, polling interval, and related settings.
- **Delivery and operation records:** Feed entry identifiers, publication timestamps, delivery timestamps, Discord message IDs, polling status, and error text used to prevent duplicates and troubleshoot feeds.
- **Webhook credentials:** Discord webhook IDs and tokens required to publish to configured channels. Webhook tokens are encrypted before database storage.

The App does not read or store Discord server message history or message content. It uses server, channel, and permission information needed to configure feeds, and publishes through Discord webhooks. The dashboard uses the identify and guilds OAuth scopes.

## How information is used

Information is used to authenticate dashboard users, show servers they can manage, save feed settings, fetch configured RSS and Atom URLs, deliver new posts, prevent duplicate deliveries, and diagnose errors. The operator does not sell personal information or use it for advertising.

## Sharing and service providers

Feed content is requested from the RSS and Atom websites configured by server administrators. Posts are sent to Discord through Discord's API. The hosting provider may process data stored on its infrastructure. The operator does not intentionally disclose account or feed data to other parties except as needed to operate the App, comply with law, protect the service, or respond to a valid legal request.

Feed URLs may identify the website or publisher selected by a server administrator. Feed contents and linked media come from third-party publishers and are subject to their own terms and privacy practices.

## Storage and retention

The App stores feed configuration and delivery records while a feed exists so it can continue publishing without duplicates. Deleting a feed removes its configuration, delivery history, and feed-specific webhook record from the App's database. OAuth dashboard sessions expire after seven days and can also be removed by logging out. Expired sessions are cleaned up by the service.

Database backups, if enabled by the operator, may retain deleted data for the backup rotation period: **[DESCRIBE BACKUP RETENTION OR STATE THAT BACKUPS ARE NOT KEPT]**.

## Security

OAuth and webhook tokens are encrypted before being stored in the database. The operator should use HTTPS for any public dashboard, restrict access to environment secrets and database backups, and remove credentials if the service is retired. No method of storage or transmission is completely secure.

## Your choices and requests

You can sign out of the dashboard, pause or delete feeds, and remove the App from a server. For questions or requests about stored personal information, contact **[EMAIL ADDRESS]**. Removing the App from a server does not automatically delete feed configuration from the database; use the dashboard to delete feeds or contact the operator.

## Children and changes

The App is a general-purpose Discord utility and is not designed to collect information directly from children. The operator may update this policy. The latest version and its effective date will be posted at **[PUBLIC HTTPS PRIVACY POLICY URL]**.

## Contact

**[OPERATOR NAME]**  
**[EMAIL ADDRESS]**  
**[POSTAL ADDRESS, IF REQUIRED FOR YOUR SERVICE]**