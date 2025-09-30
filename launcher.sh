#!/bin/bash
# SSTV Groundstation Launcher (jq-free)

set -euo pipefail

APP_DIR="$HOME/sstv-groundstation"
REPO_URL="https://github.com/Mraanderson/sstv-groundstation.git"
BACKUP_ROOT="$HOME/sstv-backups"
PORT="${PORT:-5000}"
ENV="${ENV:-development}"

GREEN="\033[92m"; RED="\033[91m"; YELLOW="\033[93m"; RESET="\033[0m"

msg() { echo -e "$1$2${RESET}"; }

# --- JSON parsing without jq ---
json_get() {
  local key=$1 file=$2
  grep -o "\"$key\"[[:space:]]*:[[:space:]]*[^,}]*" "$file" \
    | sed 's/.*: *//; s/[",]//g'
}

# --- Virtualenv ---
ensure_venv() {
  cd "$APP_DIR"
  if [ ! -d "venv" ]; then
    msg "$YELLOW" "Creating virtual environment..."
    python3 -m venv venv
  fi
  # shellcheck disable=SC1091
  source venv/bin/activate
  if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
  fi
}

# --- Git helpers ---
clone_if_missing() {
  if [ ! -d "$APP_DIR/.git" ]; then
    msg "$YELLOW" "Cloning repo..."
    git clone -b main "$REPO_URL" "$APP_DIR"
  fi
}

pull_update() {
  cd "$APP_DIR"
  git fetch origin
  git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"
}

switch_branch() {
  local branch=$1
  cd "$APP_DIR"
  git fetch origin "$branch"
  git checkout "$branch" || git checkout -b "$branch" "origin/$branch"
  git pull --ff-only origin "$branch"
}

# --- Backup & restore ---
do_backup() {
  mkdir -p "$BACKUP_ROOT"
  TS=$(date +%Y%m%d_%H%M%S)
  DEST="$BACKUP_ROOT/$TS"
  mkdir -p "$DEST"
  [ -d "$APP_DIR/recordings" ] && cp -r "$APP_DIR/recordings" "$DEST/"
  [ -d "$APP_DIR/app/static/gallery" ] && cp -r "$APP_DIR/app/static/gallery" "$DEST/"
  msg "$GREEN" "Backup saved to $DEST"
}

do_restore() {
  shopt -s nullglob
  backups=("$BACKUP_ROOT"/*)
  shopt -u nullglob
  [ ${#backups[@]} -eq 0 ] && { msg "$RED" "No backups found"; exit 1; }
  echo "Select a backup:"
  select dir in "${backups[@]}"; do
    [ -n "$dir" ] || { msg "$RED" "Invalid"; exit 1; }
    [ -d "$dir/recordings" ] && cp -r "$dir/recordings" "$APP_DIR/"
    [ -d "$dir/gallery" ] && cp -r "$dir/gallery" "$APP_DIR/app/static/"
    msg "$GREEN" "Restored from $dir"
    break
  done
}

do_reclone() {
  read -r -p "Backup before delete? (y/n): " ans
  [[ "$ans" =~ ^[Yy]$ ]] && do_backup
  rm -rf "$APP_DIR"
  git clone -b main "$REPO_URL" "$APP_DIR"
  ensure_venv
}

# --- Run app ---
run_local() {
  clone_if_missing
  ensure_venv
  msg "$GREEN" "Launching Flask app..."
  export FLASK_APP=run.py
  export FLASK_ENV="$ENV"
  flask run --host=0.0.0.0 --port="$PORT"
}

# --- Start with TLE update + recording ---
start_with_tle_and_recording() {
  clone_if_missing
  ensure_venv
  CFG_FILE="$APP_DIR/settings.json"
  [ -f "$CFG_FILE" ] || { msg "$RED" "settings.json missing"; exit 1; }
  LAT=$(json_get latitude "$CFG_FILE")
  LON=$(json_get longitude "$CFG_FILE")
  if [ -z "$LAT" ] || [ -z "$LON" ]; then
    msg "$RED" "Location not set in settings.json"
    exit 1
  fi
  msg "$GREEN" "Updating TLE..."
  source "$APP_DIR/venv/bin/activate"
  python3 -m app.utils.tle_updater || true
  msg "$GREEN" "Starting scheduler..."
  python3 app/utils/sdr_scheduler.py
}

# --- Admin menu ---
admin_menu() {
  while true; do
    echo "------ Admin Menu ------"
    echo "1) Pull latest changes"
    echo "2) Switch branch"
    echo "3) Backup recordings/images"
    echo "4) Restore recordings/images"
    echo "5) Clear & reclone"
    echo "6) Back"
    read -r -p "Choice: " c
    case $c in
      1) pull_update ;;
      2) read -r -p "Branch: " br; switch_branch "$br" ;;
      3) do_backup ;;
      4) do_restore ;;
      5) do_reclone ;;
      6) break ;;
    esac
  done
}

# --- Main menu ---
main_menu() {
  while true; do
    echo "=============================="
    echo "   SSTV Groundstation Launcher"
    echo "=============================="
    echo "1) Run local install"
    echo "2) Start (update TLE + recording)"
    echo "3) Admin options"
    echo "4) Exit"
    read -r -p "Choice: " c
    case $c in
      1) run_local ;;
      2) start_with_tle_and_recording ;;
      3) admin_menu ;;
      4) exit 0 ;;
    esac
  done
}

# --- Arg parsing ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    -r) run_local; exit 0 ;;
    -s) start_with_tle_and_recording; exit 0 ;;
    -u) pull_update; exit 0 ;;
    -b) switch_branch "$2"; exit 0 ;;
    --backup) do_backup; exit 0 ;;
    --restore) do_restore; exit 0 ;;
    --reclone) do_reclone; exit 0 ;;
    -p) PORT="$2"; shift 2 ;;
    -e) ENV="$2"; shift 2 ;;
    -h|--help) echo "Use -r, -s, -u, -b, --backup, --restore, --reclone"; exit 0 ;;
    *) echo "Unknown option $1"; exit 1 ;;
  esac
done

main_menu
