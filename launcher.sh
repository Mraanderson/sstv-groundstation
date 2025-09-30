#!/bin/bash
set -euo pipefail

APP_DIR="$HOME/sstv-groundstation"
REPO_URL="https://github.com/Mraanderson/sstv-groundstation.git"
BACKUP_DIR="$HOME/sstv-backups"

GREEN="\033[92m"; RED="\033[91m"; YELLOW="\033[93m"; RESET="\033[0m"

usage() {
  cat <<EOF
SSTV Groundstation Launcher
===========================

This script manages the entire groundstation app. Everything (code, recordings,
images) lives inside: $APP_DIR

⚠️  If you delete that folder, you delete your recordings and images unless you back them up.
Backups are stored under: $BACKUP_DIR

Usage: $0 [options]

Options:
  -r            Run local install (default if folder exists)
  -s            Start with TLE update + recording (requires location set)
  -u            Pull latest changes (main branch)
  -b <branch>   Switch to a specific branch
  --backup      Backup recordings/images to $BACKUP_DIR
  --restore     Restore recordings/images from a backup
  --reclone     Clear & reclone repo (with backup prompt)
  -h, --help    Show this help menu
EOF
  exit 0
}

# --- Functions ---

run_local() {
  if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}No local install found. Clone first.${RESET}"
    exit 1
  fi
  cd "$APP_DIR"
  source venv/bin/activate
  export FLASK_APP=run.py
  export FLASK_ENV=development
  flask run --host=0.0.0.0 --port=5000
}

start_with_tle_and_recording() {
  CFG_FILE="$APP_DIR/settings.json"
  if [ ! -f "$CFG_FILE" ]; then
    echo -e "${RED}No config file found. Please configure location first.${RESET}"
    exit 1
  fi
  LAT=$(jq -r '.latitude' "$CFG_FILE")
  LON=$(jq -r '.longitude' "$CFG_FILE")
  if [ "$LAT" = "null" ] || [ "$LON" = "null" ]; then
    echo -e "${RED}Location not set in config. Cannot start recording.${RESET}"
    exit 1
  fi
  echo -e "${GREEN}Updating TLE data...${RESET}"
  source "$APP_DIR/venv/bin/activate"
  python3 -m app.utils.tle_updater
  echo -e "${GREEN}Starting scheduler/recording...${RESET}"
  python3 app/utils/sdr_scheduler.py
}

pull_update() {
  cd "$APP_DIR"
  git fetch origin
  LOCAL=$(git rev-parse @)
  REMOTE=$(git rev-parse @{u})
  if [ "$LOCAL" != "$REMOTE" ]; then
    echo -e "${YELLOW}Update available. Pulling...${RESET}"
    git pull
  else
    echo -e "${GREEN}Already up to date.${RESET}"
  fi
}

switch_branch() {
  local branch=$1
  cd "$APP_DIR"
  git fetch origin
  git checkout "$branch"
  git pull origin "$branch"
}

do_backup() {
  TS=$(date +%Y%m%d_%H%M%S)
  DEST="$BACKUP_DIR/$TS"
  mkdir -p "$DEST"
  cp -r "$APP_DIR/recordings" "$DEST/" 2>/dev/null || true
  cp -r "$APP_DIR/app/static/gallery" "$DEST/" 2>/dev/null || true
  echo -e "${GREEN}Backup saved to $DEST${RESET}"
}

do_restore() {
  echo "Available backups:"
  select dir in "$BACKUP_DIR"/*; do
    [ -n "$dir" ] || { echo "Invalid selection"; exit 1; }
    cp -r "$dir/recordings" "$APP_DIR/" 2>/dev/null || true
    cp -r "$dir/gallery" "$APP_DIR/app/static/" 2>/dev/null || true
    echo -e "${GREEN}Restored from $dir${RESET}"
    break
  done
}

do_reclone() {
  echo -e "${YELLOW}This will delete $APP_DIR. Back up first!${RESET}"
  read -p "Backup before delete? (y/n): " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then do_backup; fi
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
}

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case $1 in
    -r) run_local; exit 0 ;;
    -s) start_with_tle_and_recording; exit 0 ;;
    -u) pull_update; exit 0 ;;
    -b) switch_branch "$2"; exit 0 ;;
    --backup) do_backup; exit 0 ;;
    --restore) do_restore; exit 0 ;;
    --reclone) do_reclone; exit 0 ;;
    -h|--help) usage ;;
    *) echo -e "${RED}Unknown option: $1${RESET}"; usage ;;
  esac
done

# Default: show help if no args
usage
