# Размещение FeedFlow в Oracle Cloud (Always Free)

Эта инструкция разворачивает один экземпляр FeedFlow на Ubuntu VM. Docker Compose запускает Discord-бота, веб-панель, SQLite на постоянном Docker volume и Caddy для HTTPS. Порт приложения 8000 остаётся внутренним; из интернета доступны только 80/443 для панели и 22 для SSH.

## Перед началом

Oracle Cloud Always Free — наиболее подходящий бесплатный вариант для текущей архитектуры FeedFlow: один процесс постоянно держит соединение с Discord и пишет состояние в SQLite. Текущая квота OCI Ampere A1 Always Free — суммарно до 2 OCPU и 12 GB RAM в домашнем регионе. Для этого проекта достаточно VM `VM.Standard.A1.Flex` с 1 OCPU и 6 GB RAM и стандартным загрузочным диском 50 GB. При создании обязательно выберите образ и ресурсы с отметкой **Always Free eligible**.

У этого варианта нет гарантии бесперебойной работы. Oracle пишет, что может забрать бесплатную VM, если за 7 дней загрузка CPU (95-й перцентиль), сети и, для A1, памяти будет ниже 20%. У RSS-бота обычно низкая нагрузка, поэтому такое предупреждение существенно. Также в домашнем регионе может временно не быть свободных VM. Для важного бота с гарантией 24/7 нужен недорогой платный VPS.

Регистрация Free Tier обычно требует подтверждения телефона и банковской карты. В бесплатной учётной записи не создавайте ресурсы без отметки **Always Free eligible** и не переходите на платный тариф, если не хотите оплачивать использование сверх бесплатных лимитов.

Другие популярные бесплатные варианты для этой версии проекта не подходят:

- **Render Free** выключает web service после 15 минут без входящих запросов. При остановке теряется локальная SQLite-база; бесплатного постоянного диска нет.
- **Koyeb Free** засыпает после часа без входящего трафика; бесплатный экземпляр нельзя использовать как Worker и нельзя подключить постоянный volume.
- **Google Cloud Free Tier** даёт небольшую VM только в трёх регионах США, до 1 GB исходящего трафика в месяц; внешняя IPv4-адресация тарифицируется отдельно. Это добавляет риск счёта и задержки для сервера, поэтому здесь выбран OCI.

## 1. Создайте VM в Oracle Cloud

1. Создайте аккаунт в [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/). Выберите домашний регион внимательно: Always Free VM создаётся только в нём.
2. В **Compute → Instances → Create instance** задайте имя, например `feedflow`.
3. Выберите Ubuntu 24.04 ARM64 и shape `VM.Standard.A1.Flex`. Выставьте 1 OCPU и 6 GB памяти, проверьте отметку **Always Free eligible**.
4. Укажите публичную подсеть и включите назначение публичного IPv4. Для загрузочного диска оставьте стандартные 50 GB.
5. Для SSH создайте новую пару ключей. Скачайте приватный ключ в безопасное место; передавайте на сервер только публичный ключ.
6. После создания сохраните публичный IPv4 адрес VM.

Если появляется `Out of host capacity`, это означает, что сейчас нет свободной машины в выбранной зоне. Попробуйте другую availability domain, если она доступна, или повторите позже. Не выбирайте платную форму вместо Always Free.

### Откройте сетевые порты

В **Networking → Virtual Cloud Networks → ваша VCN → Security Lists** добавьте stateful ingress-правила:

| Протокол | Порт | Source |
| --- | ---: | --- |
| TCP | 22 | Ваш текущий публичный IP `/32` (лучше) |
| TCP | 80 | `0.0.0.0/0` |
| TCP | 443 | `0.0.0.0/0` |
| UDP | 443 | `0.0.0.0/0` (необязательно, для HTTP/3) |

Для SSH можно временно указать `0.0.0.0/0`, если ваш IP меняется, а позже ограничить его. Входящий 8000 открывать не нужно: панель принимает Caddy внутри Docker-сети.

## 2. Подготовьте домен и HTTPS

Discord OAuth требует постоянный внешний адрес панели. Бесплатный поддомен можно создать на [DuckDNS](https://www.duckdns.org/): выберите имя вроде `feedflow-supernova.duckdns.org` и укажите публичный IPv4 VM. Если IP VM когда-либо изменится, обновите его в DuckDNS.

Caddy из подготовленной Compose-конфигурации сам получает и продлевает HTTPS-сертификат. Для этого DNS-имя должно уже указывать на VM, а порты 80 и 443 должны быть доступны извне. Вручную выпускать сертификат не надо.

## 3. Подключитесь к VM и установите Docker

На Windows откройте PowerShell. Укажите путь к скачанному приватному SSH-ключу и IPv4 VM:

```powershell
ssh -i "$env:USERPROFILE\.ssh\feedflow-oci.key" ubuntu@<PUBLIC_IP>
```

Если ключ сохранён в другом месте, замените путь. При первом подключении подтвердите fingerprint сервера. Затем установите Docker Engine и Compose официальным репозиторием Docker:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin unzip
sudo systemctl enable --now docker
```

В репозитории проекта также есть скрипт `install-docker.sh`, выполняющий те же команды.

## 4. Передайте проект с Windows на сервер

В локальном PowerShell перейдите в папку проекта и создайте архив:

```powershell
cd "D:\AI ChatGPT_Codex\Coding\rss_discord_bot"
python .\deploy\package.py
scp -i "$env:USERPROFILE\.ssh\feedflow-oci.key" .\feedflow-deploy.zip ubuntu@<PUBLIC_IP>:/home/ubuntu/
```

Архив содержит исходники и deployment-конфигурацию. Скрипт упаковки исключает `.env`, `tokens.txt`, локальную базу, виртуальное окружение и кеши. Приватный SSH-ключ также остаётся на вашем ПК.

Подключитесь к VM по SSH и распакуйте проект:

```bash
mkdir -p ~/feedflow
unzip -o ~/feedflow-deploy.zip -d ~/feedflow
cd ~/feedflow/deploy/oracle
cp cloud.env.example .env
nano .env
```

Заполните в `.env`:

- `DISCORD_BOT_TOKEN`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET` — значения вашего приложения в Discord Developer Portal.
- `APP_DOMAIN` — точный домен DuckDNS без `https://`.
- `APP_BASE_URL` — `https://` и тот же домен.
- `SESSION_SECRET` и `WEBHOOK_ENCRYPTION_KEY` — новые секреты для свежей базы; команды генерации ниже.
- Остальные параметры можно оставить как есть.

Выйдите из редактора nano: `Ctrl+O`, `Enter`, `Ctrl+X`. Ограничьте доступ к файлу с секретами:

```bash
chmod 600 .env
```

Для новых секретов сгенерируйте значения на VM:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
```

Вставьте первый результат в `SESSION_SECRET`, второй — в `WEBHOOK_ENCRYPTION_KEY`. Сохраните `WEBHOOK_ENCRYPTION_KEY` в надёжном месте: без него нельзя восстановить зашифрованные токены из резервной копии базы. Не публикуйте содержимое `.env` и не отправляйте его в чат.

## 5. Настройте Discord OAuth и запустите

1. Откройте ваше приложение в Discord Developer Portal → **OAuth2**.
2. Добавьте redirect URI с точным доменом: `https://<ВАШ_ДОМЕН>/auth/callback`.
3. Сохраните изменения.
4. В SSH-терминале, находясь в `~/feedflow/deploy/oracle`, запустите:

   ```bash
   sudo docker compose up -d --build
   ```

5. Проверьте запуск и логи:

   ```bash
   sudo docker compose ps
   sudo docker compose logs -f --tail=100
   ```

6. Откройте `https://<ВАШ_ДОМЕН>` и войдите через Discord.

Если Caddy не получает сертификат, проверьте, что DuckDNS уже разрешается в публичный IP VM и порты 80/443 открыты одновременно в OCI Security List и на VM. Логи Caddy доступны командой `sudo docker compose logs -f caddy`.

## 6. Перенесите уже настроенные ленты (по желанию)

Если нужно перенести ленты с локального ПК, сначала остановите локальный FeedFlow через `Ctrl+C`, чтобы SQLite успела сохранить изменения и одновременно не работали два экземпляра бота. После распаковки проекта, но до запуска на VM, в PowerShell выполните:

```powershell
scp -i "$env:USERPROFILE\.ssh\feedflow-oci.key" .\data\rssbot.sqlite3 ubuntu@<PUBLIC_IP>:/home/ubuntu/rssbot.sqlite3
```

На VM запустите Compose один раз, чтобы создать volume, затем остановите только приложение, скопируйте базу в контейнер и снова запустите его:

```bash
cd ~/feedflow/deploy/oracle
sudo docker compose up -d --build
sudo docker compose stop app
APP_CONTAINER=$(sudo docker compose ps -aq app)
sudo docker cp /home/ubuntu/rssbot.sqlite3 "$APP_CONTAINER:/data/rssbot.sqlite3"
sudo docker compose start app
```

Для работы перенесённой базы вставьте в cloud `.env` тот же `WEBHOOK_ENCRYPTION_KEY`, который использовался локально. Иначе сохранённые Discord OAuth/webhook tokens не расшифруются. После переноса проверьте панель и тестовую отправку. Не запускайте локальный и облачный экземпляры одновременно: у них разные копии SQLite, и они могут продублировать публикации.

## 7. Управление и резервная копия

Все команды выполняются по SSH в `~/feedflow/deploy/oracle`:

```bash
sudo docker compose ps                         # статус
sudo docker compose logs -f --tail=100         # логи
sudo docker compose restart app                # перезапуск бота и панели
sudo docker compose down                       # остановить; данные volume сохраняются
sudo docker compose up -d                      # снова запустить
```

База лежит в постоянном Docker volume `feedflow-data`; сертификаты Caddy хранятся отдельно в `caddy-data`. Чтобы создать согласованную SQLite-копию, запустите скрипт из deployment-папки:

```bash
bash backup.sh
```

Он положит файл в `~/feedflow-backups`. Скачайте его на Windows командой `scp`, указав настоящее имя файла из вывода скрипта. При удалении самой VM данные volume удалятся вместе с диском, поэтому регулярно скачивайте базу и храните копию `.env` отдельно. Для восстановления сохраните тот же `WEBHOOK_ENCRYPTION_KEY`.

## Полезные официальные страницы

- [Oracle Cloud Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Oracle Cloud Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)
- [Oracle: запуск первой Linux VM](https://docs.oracle.com/en-us/iaas/Content/Compute/tutorials/first-linux-instance/overview.htm)
- [Docker Engine для Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Caddy: автоматический HTTPS](https://caddyserver.com/docs/automatic-https)
- [DuckDNS](https://www.duckdns.org/)
