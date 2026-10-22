# Deploy FeedFlow on Oracle Cloud

This guide covers an Ubuntu virtual machine in Oracle Cloud Infrastructure (OCI). The application setup uses the Docker Compose files in deploy/oracle.

## Before you create resources

OCI Free Tier limits, eligibility, capacity, and billing rules can change. Check the current [Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) and [Free Tier terms](https://www.oracle.com/cloud/free/) before creating anything. Confirm that every selected resource is marked Always Free eligible if you do not intend to use paid resources. Free capacity may be unavailable, and a free instance is not a guaranteed 24/7 service.

## Create the VM

1. Create a Compute instance in your OCI home region.
2. Choose a currently supported Ubuntu LTS image. An ARM64 shape is supported by the project Docker image; confirm its eligibility and current quota in your account.
3. Assign a public IPv4 address and add an SSH public key. Keep the private key on your computer.
4. Save the VM's public IP address.

## Open network ports

In the VCN security list or network security group, allow these inbound connections:

| Protocol | Port | Source |
| --- | ---: | --- |
| TCP | 22 | Your current public IP with /32 when possible |
| TCP | 80 | 0.0.0.0/0 |
| TCP | 443 | 0.0.0.0/0 |
| UDP | 443 | 0.0.0.0/0, optional for HTTP/3 |

Restrict SSH to your IP when possible. Do not expose port 8000. Also configure the VM firewall after connecting.

## Connect and prepare a domain

From Windows PowerShell, connect using the private key downloaded during VM creation:

~~~powershell
ssh -i "$env:USERPROFILE\.ssh\feedflow-oci.key" ubuntu@<PUBLIC_IP>
~~~

Install the local firewall and allow SSH and web traffic:

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

Point a public domain or subdomain to the VM's IPv4 address. Caddy will obtain and renew the HTTPS certificate after DNS resolves and ports 80 and 443 are reachable.

## Install FeedFlow

Download the deployment archive from the [latest GitHub Release](https://github.com/supernova47/rss-discord-bot/releases/latest), then extract it on the VM:

~~~bash
mkdir -p ~/feedflow
curl -fL https://github.com/supernova47/rss-discord-bot/releases/latest/download/feedflow-deploy.zip -o ~/feedflow-deploy.zip
unzip -o ~/feedflow-deploy.zip -d ~/feedflow
cd ~/feedflow/deploy/oracle
cp cloud.env.example .env
nano .env
~~~

Fill in DISCORD_BOT_TOKEN, DISCORD_CLIENT_ID, and DISCORD_CLIENT_SECRET. Set APP_DOMAIN to your hostname without https:// and APP_BASE_URL to the same hostname with https://. Generate SESSION_SECRET and WEBHOOK_ENCRYPTION_KEY:

~~~bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
~~~

Put the first value in SESSION_SECRET and the second in WEBHOOK_ENCRYPTION_KEY. Save the file with Ctrl+O, Enter, Ctrl+X, then restrict access:

~~~bash
chmod 600 .env
~~~

In Discord Developer Portal, add this OAuth2 redirect URI:

~~~text
https://<YOUR_DOMAIN>/auth/callback
~~~

Start the services and check their status:

~~~bash
cd ~/feedflow/deploy/oracle
sudo bash install-docker.sh
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs --tail=100
~~~

Open https://<YOUR_DOMAIN> and sign in with Discord. If Caddy cannot obtain a certificate, check the DNS record, both OCI and VM firewall rules, and Caddy's logs:

~~~bash
sudo docker compose logs -f caddy
~~~

## Optional: move an existing database

Stop the local FeedFlow process with Ctrl+C before copying its database. Use the same WEBHOOK_ENCRYPTION_KEY on the VM as on the local installation.

From Windows PowerShell, copy the SQLite file:

~~~powershell
scp -i "$env:USERPROFILE\.ssh\feedflow-oci.key" .\data\rssbot.sqlite3 ubuntu@<PUBLIC_IP>:/home/ubuntu/rssbot.sqlite3
~~~

On the VM, create the volume, stop only the app, copy the database into it, and start the app:

~~~bash
cd ~/feedflow/deploy/oracle
sudo docker compose up -d --build
sudo docker compose stop app
APP_CONTAINER="$(sudo docker compose ps -aq app)"
sudo docker cp /home/ubuntu/rssbot.sqlite3 "$APP_CONTAINER:/data/rssbot.sqlite3"
sudo docker compose start app
~~~

Sign in to the dashboard and test a feed. Do not run the local and VM instances at the same time.

## Backups and updates

Create a consistent SQLite backup:

~~~bash
cd ~/feedflow/deploy/oracle
bash backup.sh
~~~

Download the backup away from the VM and keep it with the matching WEBHOOK_ENCRYPTION_KEY. For routine updates, follow [Update FeedFlow from a GitHub Release](../UPDATE.md). Never remove Docker volumes during an update.