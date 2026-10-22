# Размещение FeedFlow на Selectel VDS

Эта инструкция разворачивает один экземпляр FeedFlow на Ubuntu-сервере Selectel. Docker Compose запускает бота и панель, хранит SQLite в постоянном Docker volume и поднимает Caddy для HTTPS. Из интернета открыты только SSH и веб-порты 80/443; порт приложения 8000 доступен только внутри Docker-сети.

## Какой тариф выбрать

Для начала выберите **VDS 1-2-25**: 1 vCPU, 2 ГБ RAM, NVMe-диск 25 ГБ — сейчас на странице Selectel указана цена **250 ₽/мес.** В конфигурацию VDS также входит один публичный IP-адрес и 3 ТБ внешнего трафика в месяц. Если на сервере появится больше приложений или нагрузка вырастет, конфигурацию можно изменить; следующий небольшой тариф — 2 vCPU, 2 ГБ RAM и 40 ГБ диска.

Оплата банковскими картами проводится через PayU; Selectel указывает, что принимает карты МИР и не взимает комиссию за пополнение. Уточните итоговую цену в панели перед созданием сервера: тарифы могут изменяться.

Полезные страницы:

- [Тарифы VDS Selectel](https://selectel.ru/services/cloud/vps-vds/)
- [Способы оплаты](https://vds.selectel.ru/ru/pmethods.html)
- [Создание VDS](https://docs.selectel.ru/vds-servers/create-server/)
- [Подключение к VDS](https://docs.selectel.ru/vds-servers/manage/connect-to-server/)
- [Что входит в VDS и ограничения](https://docs.selectel.ru/vds-servers/about/about-vds-server/)

## 1. Создайте сервер

1. Зарегистрируйтесь в Selectel и пополните баланс удобной российской картой.
2. В панели управления откройте **Продукты → VDS-серверы → Создать сервер**.
3. Назовите сервер, например `feedflow`, выберите регион **Москва** или **Санкт-Петербург** и образ **Ubuntu 24.04 LTS x86_64**.
4. Выберите конфигурацию **VDS 1-2-25**.
5. Добавьте SSH-ключ. Если его ещё нет, создайте на компьютере в PowerShell:

   ```powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
   ssh-keygen -t ed25519 -C "feedflow-selectel" -f "$env:USERPROFILE\.ssh\feedflow-selectel"
   Get-Content "$env:USERPROFILE\.ssh\feedflow-selectel.pub"
   ```

   В Selectel вставьте содержимое файла `.pub`. Приватный файл `feedflow-selectel` никому не отправляйте. Сохраните его на своём ПК.

6. Создайте сервер и скопируйте его публичный IPv4 из панели. В панели также найдите логин пользователя для SSH.

## 2. Назначьте домен панели

Discord OAuth требует постоянный HTTPS-адрес. Можно использовать свой домен или бесплатный поддомен на [DuckDNS](https://www.duckdns.org/). Создайте поддомен и укажите в DuckDNS публичный IPv4 сервера.

Перед запуском проверьте, что имя домена уже указывает на этот IPv4. Caddy автоматически выпустит и будет продлевать HTTPS-сертификат, когда домен доступен снаружи, а порты 80 и 443 открыты.

## 3. Подключитесь и откройте порты

В PowerShell замените `ЛОГИН` и `IP_СЕРВЕРА` значениями из панели Selectel:

```powershell
ssh -i "$env:USERPROFILE\.ssh\feedflow-selectel" ЛОГИН@IP_СЕРВЕРА
```

На сервере разрешите SSH, HTTPS и HTTP, затем включите UFW. Правило SSH добавьте до включения файрвола, чтобы сохранить удалённый доступ:

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

## 4. Передайте проект с Windows на сервер

В локальном PowerShell перейдите в папку проекта, соберите архив и отправьте его на VDS:

```powershell
cd "D:\AI ChatGPT_Codex\Coding\rss_discord_bot"
python .\deploy\package.py
scp -i "$env:USERPROFILE\.ssh\feedflow-selectel" .\feedflow-deploy.zip ЛОГИН@IP_СЕРВЕРА:~/
```

Замените `ЛОГИН` и `IP_СЕРВЕРА`. Архив исключает `.env`, токены, локальную базу данных, виртуальное окружение и кеши.

На сервере распакуйте архив и установите Docker:

```bash
mkdir -p ~/feedflow
unzip -o ~/feedflow-deploy.zip -d ~/feedflow
sudo bash ~/feedflow/deploy/selectel/install-docker.sh
```

## 5. Настройте секреты и Discord OAuth

Перейдите в папку конфигурации, создайте рабочий `.env` и сгенерируйте два секрета:

```bash
cd ~/feedflow/deploy/selectel
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
nano .env
```

Первый сгенерированный результат вставьте в `SESSION_SECRET`, второй — в `WEBHOOK_ENCRYPTION_KEY`. В `.env` также заполните `DISCORD_BOT_TOKEN`, `DISCORD_CLIENT_ID` и `DISCORD_CLIENT_SECRET`. В `APP_DOMAIN` укажите домен без `https://`, а в `APP_BASE_URL` — тот же домен с `https://`. Оба значения должны совпадать с адресом, на который указывает DNS.

Сохраните `WEBHOOK_ENCRYPTION_KEY` в надёжном месте вместе с резервными копиями: без него нельзя расшифровать сохранённые токены вебхуков. Не публикуйте `.env` и не присылайте его в чат.

В Discord Developer Portal → **OAuth2** добавьте redirect URI с вашим настоящим доменом:

```text
https://ВАШ_ДОМЕН/auth/callback
```

В `.env` замените `APP_DOMAIN` и `APP_BASE_URL` на те же значения. Затем сохраните файл: `Ctrl+O`, `Enter`, `Ctrl+X`, и ограничьте его чтение:

```bash
chmod 600 .env
```

## 6. Запустите FeedFlow

Находясь в `~/feedflow/deploy/selectel`, выполните:

```bash
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs -f --tail=100
```

Откройте `https://ВАШ_ДОМЕН` и войдите через Discord. Если HTTPS не заработал, проверьте DNS, правила UFW и логи Caddy:

```bash
sudo docker compose logs -f caddy
```

## Перенос локальных настроек (необязательно)

Если нужно перенести уже настроенные ленты, сначала остановите локальный FeedFlow на ПК, чтобы два экземпляра не публиковали одни и те же новости. В PowerShell из папки `rss_discord_bot` отправьте базу:

```powershell
scp -i "$env:USERPROFILE\.ssh\feedflow-selectel" .\data\rssbot.sqlite3 ЛОГИН@IP_СЕРВЕРА:~/rssbot.sqlite3
```

Перед первым запуском на сервере вставьте в облачный `.env` тот же `WEBHOOK_ENCRYPTION_KEY`, который использовался локально. После загрузки архива и заполнения `.env` создайте контейнер, остановите приложение, замените базу и снова запустите:

```bash
cd ~/feedflow/deploy/selectel
sudo docker compose up -d --build
sudo docker compose stop app
APP_CONTAINER="$(sudo docker compose ps -aq app)"
sudo docker cp ~/rssbot.sqlite3 "$APP_CONTAINER:/data/rssbot.sqlite3"
sudo docker compose start app
```

Не запускайте локальный и облачный экземпляры одновременно: это две разные копии базы и планировщика, поэтому возможны дубликаты публикаций.

## Управление и резервные копии

Команды выполняются по SSH в `~/feedflow/deploy/selectel`:

```bash
sudo docker compose ps
sudo docker compose logs -f --tail=100
sudo docker compose restart app
sudo docker compose down
sudo docker compose up -d
bash backup.sh
```

`docker compose down` останавливает сервисы, но не удаляет Docker volumes. У VDS нет автоматического резервного копирования; регулярно запускайте `bash backup.sh` и скачивайте созданный файл базы на ПК. При удалении самого VDS база и сертификаты в его Docker volumes удалятся вместе с диском.
