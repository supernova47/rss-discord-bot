#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$HOME/feedflow-backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TEMP_DB="/tmp/feedflow-backup-${STAMP}.sqlite3"
BACKUP_FILE="$BACKUP_DIR/rssbot-${STAMP}.sqlite3"
CONTAINER_ID="$(sudo docker compose ps -q app)"

if [[ -z "$CONTAINER_ID" ]]; then
  echo "FeedFlow app container is not running. Start it before making a backup." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
sudo docker compose exec -T app python -c "import sqlite3; source=sqlite3.connect('/data/rssbot.sqlite3'); target=sqlite3.connect('${TEMP_DB}'); source.backup(target); target.close(); source.close()"
sudo docker cp "$CONTAINER_ID:$TEMP_DB" "$BACKUP_FILE"
sudo docker compose exec -T app rm -f "$TEMP_DB"
chmod 600 "$BACKUP_FILE"
echo "Backup created: $BACKUP_FILE"
