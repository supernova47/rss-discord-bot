# Update FeedFlow from a GitHub Release

This procedure updates a Docker Compose installation while preserving its environment file and named data volumes. It applies to the configurations under deploy/newvps, deploy/ruvds, deploy/selectel, and deploy/oracle.

The deploy/newvps directory name is retained for existing installations. If your server uses a different deployment directory, replace the path below with that directory.

If your project root is not ~/feedflow, replace that path in every command below with the existing project root. Keep the same Compose directory so Docker continues to use the existing named volumes.

## 1. Connect and back up the database

Connect to the VPS over SSH. Go to the deployment directory and create a SQLite backup:

~~~bash
cd ~/feedflow/deploy/newvps
bash backup.sh
~~~

The script prints the backup path. From Windows PowerShell, copy that exact file to your computer before continuing:

~~~powershell
scp <SSH_USER>@<VPS_IP>:~/feedflow-backups/<BACKUP_FILE_NAME> .
~~~

Keep the database backup and the WEBHOOK_ENCRYPTION_KEY from .env together; the key is required to decrypt stored webhook tokens.

## 2. Download the release archive

Choose the release tag shown on the [GitHub Releases page](https://github.com/supernova47/rss-discord-bot/releases). Replace v0.1.0 below with the tag you want to install:

~~~bash
cd ~
curl -fL https://github.com/supernova47/rss-discord-bot/releases/download/v0.1.0/feedflow-deploy.zip -o ~/feedflow-deploy.zip
unzip -l ~/feedflow-deploy.zip | head -40
~~~

The release archive contains application and deployment files. It does not contain .env, SQLite databases, Discord tokens, or local virtual environments.

## 3. Replace the application files

Extract the archive over the existing project directory:

~~~bash
unzip -o ~/feedflow-deploy.zip -d ~/feedflow
~~~

The archive does not include the server's .env file. The SQLite database and Caddy certificates live in Docker named volumes, outside the application files.

Do not run docker compose down -v. The -v option deletes the named volumes and their data.

## 4. Rebuild and restart FeedFlow

Use the same Compose directory as before:

~~~bash
cd ~/feedflow/deploy/newvps
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs --tail=100
~~~

Docker Compose rebuilds and recreates services when their image or configuration has changed, while preserving mounted volumes. Keep the service directory and Compose project name unchanged so Docker continues using the existing named volumes. See the [Docker Compose up reference](https://docs.docker.com/reference/cli/docker/compose/up/).

## 5. Confirm the update

- Check that both app and caddy containers are running.
- Open the public HTTPS dashboard and sign in with Discord.
- Check the app logs for startup errors.
- Send one test entry from the dashboard if you want to verify delivery.

If the app does not start, inspect its logs before changing the database or encryption key. Keep the pre-update backup until the updated dashboard and feed delivery have been checked.

## Notes

- Do not run the local and VPS instances at the same time if both use separate copies of the same configuration. Either instance could publish the same feed entries.
- Keep .env on the server. Do not upload it to GitHub or include it in a release archive.
- Never remove Docker volumes during a routine update.
- The release archive does not change your domain, DNS records, OAuth redirect URI, or environment secrets.
