# Размещение FeedFlow на RUVDS

Инструкция рассчитана на один постоянно работающий экземпляр FeedFlow для нескольких Discord-серверов. Docker Compose запускает бота, панель, SQLite и Caddy, который автоматически выпускает HTTPS-сертификат. Порт приложения 8000 доступен только внутри Docker-сети.

## Какой тариф выбрать

Для самого дешёвого разумного запуска выберите **«Старт Хит»**: 1 vCPU, 1 ГБ RAM, HDD 20 ГБ и один IPv4 за **279 ₽/мес.** На тарифе «Старт» за 149 ₽ только 512 МБ RAM и диск 10 ГБ — этого мало для комфортного запуска приложения, веб-панели и Docker. Для пары-тройки серверов «Старт Хит» должен подойти при обычной частоте проверки лент; это оценка для текущей нагрузки, а не гарантия при большом количестве лент или частом опросе.

У тарифа диск HDD, поэтому установка и сборка контейнера будут медленнее, чем на SSD. Руководство добавит 2 ГБ swap — это поможет пережить пики памяти во время установки и сборки. Swap на диске медленнее оперативной памяти; если начнутся ошибки нехватки памяти, следующий разумный шаг — тариф с 2 ГБ RAM.

RUVDS указывает оплату картами Visa/Mastercard/МИР, выпущенными в России, а также через СБП. У тарифов линейки «Старт» тестового периода нет. Цены и наличие перепроверьте на странице заказа перед оплатой. Наличие зависит от дата-центра: если панель пишет, что тариф недоступен, переключите локацию на другой российский дата-центр; RUVDS указывает семь доступных российских площадок для линейки «Старт».

- [Стартовые тарифы RUVDS](https://ruvds.com/ru/vps_start/)
- [Способы оплаты RUVDS](https://ruvds.com/ru/helpcenter/payment/)
- [Docker Engine для Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Engine для Debian](https://docs.docker.com/engine/install/debian/)
- [Caddy и автоматический HTTPS](https://caddyserver.com/docs/automatic-https)
- [DuckDNS](https://www.duckdns.org/)

## 1. Создайте VPS

1. Зарегистрируйтесь в RUVDS и пополните баланс доступным способом оплаты.
2. На странице заказа выберите **«Старт Хит»**, Linux и дата-центр в России. Из ОС предпочтительно выбрать **Ubuntu 24.04 LTS**; если его нет, подойдут **Debian 13** или **Debian 12**. Не выбирайте Debian 11: его официальная поддержка безопасности завершилась 31 августа 2026 года.
3. Добавьте SSH-ключ. Если ключа ещё нет, откройте PowerShell на Windows и выполните:

   ```powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
   ssh-keygen -t ed25519 -C "feedflow-ruvds" -f "$env:USERPROFILE\.ssh\feedflow-ruvds"
   Get-Content "$env:USERPROFILE\.ssh\feedflow-ruvds.pub"
   ```

   Вставьте содержимое файла `.pub` в панель. Приватный файл `feedflow-ruvds` оставьте на своём компьютере.

4. После создания сохраните публичный IPv4 и SSH-логин, которые показывает панель.

## 2. Подготовьте адрес панели

Discord OAuth требует постоянный HTTPS-адрес. Если своего домена нет, создайте бесплатный поддомен в [DuckDNS](https://www.duckdns.org/) и направьте его на публичный IPv4 VPS.

Убедитесь, что домен уже разрешается в этот IPv4. Caddy автоматически получит и будет продлевать HTTPS-сертификат, когда DNS настроен и порты 80/443 доступны из интернета.

## 3. Подключитесь, включите swap и откройте порты

В PowerShell замените `ЛОГИН` и `IP_СЕРВЕРА` значениями из панели RUVDS:

```powershell
ssh -i "$env:USERPROFILE\.ssh\feedflow-ruvds" ЛОГИН@IP_СЕРВЕРА
```

На VPS добавьте 2 ГБ swap, чтобы снизить риск нехватки памяти при сборке Docker-образа на сервере с 1 ГБ RAM:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
if ! grep -q '^/swapfile ' /etc/fstab; then echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab; fi
free -h
```

Затем разрешите SSH и веб-порты. Сначала добавьте SSH-правило, чтобы не потерять удалённый доступ:

```bash
sudo apt-get update
sudo apt-get install -y ufw
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw --force enable
sudo ufw status verbose
```

## 4. Передайте проект с Windows на VPS

В PowerShell на своём компьютере соберите архив и отправьте его на сервер:

```powershell
cd "D:\AI ChatGPT_Codex\Coding\rss_discord_bot"
python .\deploy\package.py
scp -i "$env:USERPROFILE\.ssh\feedflow-ruvds" .\feedflow-deploy.zip ЛОГИН@IP_СЕРВЕРА:~/
```

Архив исключает `.env`, токены, локальную базу данных, виртуальное окружение и кеши.

На VPS распакуйте архив и установите Docker:

```bash
mkdir -p ~/feedflow
sudo apt-get update
sudo apt-get install -y unzip
unzip -o ~/feedflow-deploy.zip -d ~/feedflow
sudo bash ~/feedflow/deploy/ruvds/install-docker.sh
```

## 5. Заполните настройки и Discord OAuth

Создайте `.env` из шаблона и сгенерируйте секреты:

```bash
cd ~/feedflow/deploy/ruvds
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
nano .env
```

Вставьте первый сгенерированный результат в `SESSION_SECRET`, второй — в `WEBHOOK_ENCRYPTION_KEY`. Заполните `DISCORD_BOT_TOKEN`, `DISCORD_CLIENT_ID` и `DISCORD_CLIENT_SECRET` из Discord Developer Portal. Укажите один и тот же домен в `APP_DOMAIN` (без `https://`) и `APP_BASE_URL` (с `https://`). Не оставляйте значения `feedflow-yourname.duckdns.org`, если выбрали другое имя.

Сохраните файл в nano сочетанием `Ctrl+O`, `Enter`, `Ctrl+X`, затем ограничьте доступ:

```bash
chmod 600 .env
```

В Discord Developer Portal откройте **OAuth2** и добавьте Redirect URI с вашим доменом:

```text
https://ВАШ_ДОМЕН/auth/callback
```

Сохраните `WEBHOOK_ENCRYPTION_KEY` отдельно от VPS вместе с резервными копиями. Если потерять его, сохранённые в базе токены вебхуков невозможно будет расшифровать. Не публикуйте `.env` и не присылайте его в чат.

## 6. Запустите FeedFlow

Из `~/feedflow/deploy/ruvds` запустите:

```bash
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs -f --tail=100
```

Когда контейнеры запустятся, откройте `https://ВАШ_ДОМЕН` и войдите через Discord. Если HTTPS не появился, проверьте DNS, сетевые правила в панели VPS и логи Caddy:

```bash
sudo docker compose logs -f caddy
```

## Перенос настроенных лент с ПК (по желанию)

Перед переносом остановите локальный FeedFlow через `Ctrl+C`. Так не будут одновременно работать два экземпляра с разными базами и рассылать дубликаты. В PowerShell из папки проекта отправьте базу на VPS:

```powershell
scp -i "$env:USERPROFILE\.ssh\feedflow-ruvds" .\data\rssbot.sqlite3 ЛОГИН@IP_СЕРВЕРА:~/rssbot.sqlite3
```

В облачном `.env` укажите тот же `WEBHOOK_ENCRYPTION_KEY`, что использовался при локальной базе. После первоначальной сборки контейнера остановите приложение и скопируйте базу:

```bash
cd ~/feedflow/deploy/ruvds
sudo docker compose up -d --build
sudo docker compose stop app
APP_CONTAINER="$(sudo docker compose ps -aq app)"
sudo docker cp ~/rssbot.sqlite3 "$APP_CONTAINER:/data/rssbot.sqlite3"
sudo docker compose start app
```

## Управление и резервные копии

Команды выполняются через SSH в `~/feedflow/deploy/ruvds`:

```bash
sudo docker compose ps
sudo docker compose logs -f --tail=100
sudo docker compose restart app
sudo docker compose down
sudo docker compose up -d
bash backup.sh
```

`docker compose down` останавливает сервисы, но сохраняет Docker volumes. `bash backup.sh` создаёт SQLite-копию в `~/feedflow-backups`; скачивайте её на компьютер через `scp`. Если удалить VPS, база и сертификаты на его диске удалятся, поэтому храните резервные копии и `.env` отдельно.
