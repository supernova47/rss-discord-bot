# Deploy FeedFlow on RUVDS

This guide covers VPS provisioning in RUVDS. The application setup uses the Docker Compose files in deploy/ruvds.

## Create the VPS

1. Create a Linux VPS in the RUVDS control panel. Choose a currently supported Ubuntu LTS or Debian release, a public IPv4 address, and enough memory and disk for Docker and your feed workload.
2. Add an SSH public key. If you do not have one, create it in Windows PowerShell:

   ~~~powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
   ssh-keygen -t ed25519 -C "feedflow-ruvds" -f "$env:USERPROFILE\.ssh\feedflow-ruvds"
   Get-Content "$env:USERPROFILE\.ssh\feedflow-ruvds.pub"
   ~~~

   Add the public key ending in .pub in the provider panel. Keep the private key on your computer.

3. Save the server's public IP address and SSH username. Confirm current prices, availability, payment methods, and regional options in the provider panel before ordering.

## Configure access and DNS

Allow SSH on TCP port 22, HTTP on TCP port 80, and HTTPS on TCP port 443 in the provider firewall. Restrict SSH to your own IP address when possible. UDP port 443 is optional for HTTP/3. Do not expose the app's port 8000.

Point a public domain or subdomain to the server's IPv4 address. Caddy will obtain and renew the HTTPS certificate after DNS resolves and ports 80 and 443 are reachable.

## Install FeedFlow

Connect over SSH:

~~~powershell
ssh -i "$env:USERPROFILE\.ssh\feedflow-ruvds" <SSH_USER>@<VPS_IP>
~~~

Follow the common [VPS setup guide](../newvps/README.md). In its commands, use deploy/ruvds in place of deploy/newvps and copy the environment template from deploy/ruvds/.env.example. The Compose service names and required OAuth values are the same.

Add the public HTTPS callback to Discord Developer Portal:

~~~text
https://<YOUR_DOMAIN>/auth/callback
~~~

Use the same domain in APP_DOMAIN and APP_BASE_URL in the server's .env file.

## Backups and updates

Use the included backup script from the deployment directory:

~~~bash
cd ~/feedflow/deploy/ruvds
bash backup.sh
~~~

For an update, follow [Update FeedFlow from a GitHub Release](../UPDATE.md). Keep the existing Compose directory, .env file, and Docker volumes.