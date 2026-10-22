# Deploy FeedFlow on Selectel VDS

This guide covers VPS provisioning in Selectel. The application setup uses the Docker Compose files in deploy/selectel.

## Create the VPS

1. In the Selectel control panel, create a VDS server and choose a currently supported Ubuntu LTS or Debian release.
2. Choose enough memory and disk for Docker and your feed workload, and assign a public IPv4 address.
3. Add an SSH public key. If you do not have one, create it in Windows PowerShell:

   ~~~powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
   ssh-keygen -t ed25519 -C "feedflow-selectel" -f "$env:USERPROFILE\.ssh\feedflow-selectel"
   Get-Content "$env:USERPROFILE\.ssh\feedflow-selectel.pub"
   ~~~

   Add the public key ending in .pub in the provider panel. Keep the private key on your computer.

4. Save the server's public IP address and SSH username. Check the provider's current configuration, price, and payment terms before ordering.

See the current [Selectel VDS documentation](https://docs.selectel.ru/vds-servers/).

## Configure access and DNS

Allow SSH on TCP port 22, HTTP on TCP port 80, and HTTPS on TCP port 443 in the provider firewall. Restrict SSH to your own IP address when possible. UDP port 443 is optional for HTTP/3. Do not expose port 8000.

Point a public domain or subdomain to the server's IPv4 address. Caddy will obtain and renew the HTTPS certificate after DNS resolves and ports 80 and 443 are reachable.

## Install FeedFlow

Connect over SSH:

~~~powershell
ssh -i "$env:USERPROFILE\.ssh\feedflow-selectel" <SSH_USER>@<VPS_IP>
~~~

Follow the common [VPS setup guide](../newvps/README.md). In its commands, use deploy/selectel in place of deploy/newvps and copy the environment template from deploy/selectel/.env.example.

Add the public HTTPS callback to Discord Developer Portal:

~~~text
https://<YOUR_DOMAIN>/auth/callback
~~~

Use the same domain in APP_DOMAIN and APP_BASE_URL in the server's .env file.

## Backups and updates

Use the included backup script from the deployment directory:

~~~bash
cd ~/feedflow/deploy/selectel
bash backup.sh
~~~

For an update, follow [Update FeedFlow from a GitHub Release](../UPDATE.md). Keep the existing Compose directory, .env file, and Docker volumes.