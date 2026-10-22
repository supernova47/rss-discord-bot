# Deploy FeedFlow on a VPS

This guide sets up one FeedFlow instance on an Ubuntu or Debian VPS with Docker Compose, a persistent SQLite volume, and Caddy-managed HTTPS.

The Compose files are under deploy/newvps, deploy/ruvds, deploy/selectel, and deploy/oracle. The deploy/newvps directory name is kept for compatibility with existing installations. The same setup can be used on XorekCloud; its VMmanager control panel is at https://vm.xorek.cloud/.

## 1. Create a VPS and point a domain to it

Choose a supported Ubuntu LTS or Debian release and assign a public IPv4 address. Select enough memory and disk for Docker and the feed workload. Check the provider's current plan, billing, and network rules before creating the server.

Create a domain or subdomain and point its A record to the VPS IPv4 address. Caddy will issue and renew the HTTPS certificate after DNS resolves and ports 80 and 443 are reachable.

Allow these inbound ports in the provider firewall:

| Protocol | Port | Purpose |
| --- | ---: | --- |
| TCP | 22 | SSH; restrict the source to your IP when possible |
| TCP | 80 | HTTPS certificate validation and HTTP redirect |
| TCP | 443 | Dashboard over HTTPS |
| UDP | 443 | Optional HTTP/3 |

Do not expose port 8000 publicly. Caddy forwards HTTPS traffic to the app inside the Docker network.

## 2. Connect over SSH

On Windows, create an SSH key if needed:

~~~powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
ssh-keygen -t ed25519 -C "feedflow-vps" -f "$env:USERPROFILE\.ssh\feedflow-vps"
Get-Content "$env:USERPROFILE\.ssh\feedflow-vps.pub"
~~~

Add the public key ending in .pub to the VPS control panel. Keep the private key on your computer. Connect using the login and IP address provided by your host:

~~~powershell
ssh -i "$env:USERPROFILE\.ssh\feedflow-vps" <SSH_USER>@<VPS_IP>
~~~

On the server, allow SSH and web traffic through the local firewall. Add the SSH rule before enabling UFW so you do not lock yourself out:

~~~bash
sudo apt-get update
sudo apt-get install -y ufw unzip
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw --force enable
sudo ufw status verbose
~~~

If the VPS has little memory, configure swap according to the operating system's documentation before building the Docker image.

## 3. Download and unpack FeedFlow

Download the deployment archive attached to the [latest GitHub Release](https://github.com/supernova47/rss-discord-bot/releases/latest):

~~~bash
mkdir -p ~/feedflow
curl -fL https://github.com/supernova47/rss-discord-bot/releases/latest/download/feedflow-deploy.zip -o ~/feedflow-deploy.zip
unzip -o ~/feedflow-deploy.zip -d ~/feedflow
cd ~/feedflow/deploy/newvps
sudo bash install-docker.sh
~~~

The archive excludes .env files, database files, Discord tokens, and local virtual environments.

## 4. Configure Discord and environment secrets

Copy the deployment example and generate two secrets:

~~~bash
cd ~/feedflow/deploy/newvps
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
nano .env
~~~

Put the first generated value in SESSION_SECRET and the second in WEBHOOK_ENCRYPTION_KEY. Fill in DISCORD_BOT_TOKEN, DISCORD_CLIENT_ID, and DISCORD_CLIENT_SECRET from the Discord Developer Portal.

Set APP_DOMAIN to your hostname without https:// and set APP_BASE_URL to the same hostname with https://. For example, if APP_DOMAIN is feedflow.example.com, APP_BASE_URL must be https://feedflow.example.com.

Save the file in nano with Ctrl+O, Enter, then Ctrl+X. Restrict access to it:

~~~bash
chmod 600 .env
~~~

In the Discord Developer Portal, add this exact OAuth2 redirect URI:

~~~text
https://<YOUR_DOMAIN>/auth/callback
~~~

Keep WEBHOOK_ENCRYPTION_KEY outside the VPS with your backups. If it is lost, FeedFlow cannot decrypt the stored webhook tokens. Never publish .env or send it in chat.

Optional Telegram alerts use TELEGRAM_ALERT_BOT_TOKEN and TELEGRAM_ALERT_CHAT_ID. Leave both empty to disable them.

## 5. Start FeedFlow

From the deployment directory, build and start the app and Caddy:

~~~bash
cd ~/feedflow/deploy/newvps
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs -f --tail=100
~~~

Open https://<YOUR_DOMAIN> and sign in with Discord. If HTTPS does not become available, confirm that the domain resolves to the VPS IP and that ports 80 and 443 are allowed by both the provider firewall and UFW. Check Caddy's logs with:

~~~bash
sudo docker compose logs -f caddy
~~~

## 6. Optional: move an existing local database

Stop the local FeedFlow process with Ctrl+C before copying its database. Do not run the local and VPS instances at the same time.

From the project folder on Windows, copy the database to the VPS:

~~~powershell
scp -i "$env:USERPROFILE\.ssh\feedflow-vps" .\data\rssbot.sqlite3 <SSH_USER>@<VPS_IP>:~/rssbot.sqlite3
~~~

Use the same WEBHOOK_ENCRYPTION_KEY from the local .env on the VPS. Start Compose once to create its volumes, stop only the app, copy the database into the volume, then start the app:

~~~bash
cd ~/feedflow/deploy/newvps
sudo docker compose up -d --build
sudo docker compose stop app
APP_CONTAINER="$(sudo docker compose ps -aq app)"
sudo docker cp ~/rssbot.sqlite3 "$APP_CONTAINER:/data/rssbot.sqlite3"
sudo docker compose start app
~~~

Sign in to the dashboard and send a test entry to confirm the moved feeds work.

## Backups and updates

Create a consistent SQLite backup from the deployment directory:

~~~bash
cd ~/feedflow/deploy/newvps
bash backup.sh
~~~

Download the backup to another computer and keep it with the matching WEBHOOK_ENCRYPTION_KEY.

For future updates, follow [Update FeedFlow from a GitHub Release](../UPDATE.md). Do not remove Docker volumes during routine updates.