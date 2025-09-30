#!/bin/bash
# SSTV Groundstation Launcher
# Manages install, updates, backups, restores, branch switches, TLE update + recording, and running the app.

set -euo pipefail

# --- Constants ---
APP_DIR="$HOME/sstv-groundstation"
REPO_URL="https://github.com/Mraanderson/sstv-groundstation.git"
BACKUP_ROOT="$HOME/sstv-backups"
PORT="${PORT:-5000}"
ENV="${ENV:-development}"

GREEN="\033[92m"; RED="\033[91m"; YELLOW="\033[93m"; BLUE="\033[94m"; RESET="\033[0m"

# --- Helpers ---
msg() { echo -e "$1$2${RESET}"; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || { msg "$RED" "Error: '$1' not found"; exit 1; }; }
ensure_dir() { mkdir -p "$1"; }

usage() {
  cat <<EOF
SSTV Groundstation Launcher
===========================

Everything (code, recordings, decoded images) lives inside: $APP_DIR
Backups are stored under: $BACKUP_ROOT

Options:
  -r              Run local install (Flask app)
  -s              Start with TLE update + recording (requires location set)
  -u              Pull latest changes (main branch)
  -b <branch>     Switch to a specific branch
  --backup        Backup recordings/images to $BACKUP_ROOT
  --restore       Restore recordings/images from a backup
  --reclone       Clear & reclone repo (with backup prompt)
  -p <port>       Set Flask port (default: $PORT)
  -e <env>        Set Flask environment (default: $ENV)
  -h, --help      Show this help

Run with no arguments to use the interactive menu.
EOF
}

# --- Dependency checks ---
check_deps() {
  need_cmd git
  need_cmd python3
  need_cmd jq
}

# --- Virtualenv and dependencies ---
ensure_venv() {
  if [ ! -d "$APP_DIR" ]; then
    msg "$RED" "No local install found at $APP_DIR. Clone or reclone first."
    exit 1
  fi
  cd "$APP_DIR"
  if [ ! -d "venv" ]; then
    msg "$YELLOW" "Creating virtual environment..."
    python3 -m venv venv
  fi
  # shellcheck disable=SC1091
  source venv/bin/activate
  if [ -f "requirements.txt" ]; then
    msg "$BLUE" "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
  fi
}

# --- Git helpers ---
git_update_notice() {
  cd "$APP_DIR"
  # Ensure upstream is set to origin/$(current_branch)
  current_branch=$(git rev-parse --abbrev-ref HEAD || echo "main")
  git fetch origin "$current_branch" >/dev/null 2>&1 || true
  if git rev-parse --abbrev-ref "@{u}" >/dev/null 2>&1; then
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})
    if [ "$LOCAL" != "$REMOTE" ]; then
      msg "$YELLOW" "Update available for branch '$current_branch'. Use -u or Admin → Pull latest."
    else
      msg "$GREEN" "Branch '$current_branch' is up to date."
    fi
  else
    # Try to set upstream if origin has the branch
    if git show-ref --verify --quiet "refs/remotes/origin/$current_branch"; then
      git branch --set-upstream-to "origin/$current_branch" "$current_branch" || true
    fi
  fi
}

pull_update() {
  cd "$APP_DIR"
  current_branch=$(git rev-parse --abbrev-ref HEAD || echo "main")
  msg "$BLUE" "Fetching latest for '$current_branch'..."
  git fetch origin "$current_branch"
  git pull --ff-only origin "$current_branch"
  msg "$GREEN" "Updated '$current_branch'."
}

switch_branch() {
  local branch=$1
  [ -z "$branch" ] && { msg "$RED" "Branch name required"; exit 1; }
  cd "$APP_DIR"
  msg "$BLUE" "Switching to branch '$branch'..."
  git fetch origin "$branch"
  # Create local branch tracking remote if needed
  if git show-ref --verify --quiet "refs/heads/$branch"; then
    git checkout "$branch"
  else
    git checkout -b "$branch" "origin/$branch"
  fi
  git pull --ff-only origin "$branch" || true
  msg "$GREEN" "Now on branch '$branch'."
}

clone_if_missing() {
  if [ ! -d "$APP_DIR/.git" ]; then
    msg "$YELLOW" "No repo found at $APP_DIR. Cloning 'main'..."
    ensure_dir "$(dirname "$APP_DIR")"
    git clone -b main "$REPO_URL" "$APP_DIR"
  fi
}

# --- Backup & restore ---
do_backup() {
  ensure_dir "$BACKUP_ROOT"
  TS=$(date +%Y%m%d_%H%M%S)
  DEST="$BACKUP_ROOT/$TS"
  ensure_dir "$DEST"
  msg "$BLUE" "Backing up recordings and gallery to: $DEST"
  [ -d "$APP_DIR/recordings" ] && cp -r "$APP_DIR/recordings" "$DEST/" || msg "$YELLOW" "No recordings folder found."
  [ -d "$APP_DIR/app/static/gallery" ] && cp -r "$APP_DIR/app/static/gallery" "$DEST/" || msg "$YELLOW" "No gallery folder found."
  msg "$GREEN" "Backup complete: $DEST"
}

do_restore() {
  ensure_dir "$BACKUP_ROOT"
  shopt -s nullglob
  backups=("$BACKUP_ROOT"/*)
  shopt -u nullglob
  if [ ${#backups[@]} -eq 0 ]; then
    msg "$RED" "No backups found in $BACKUP_ROOT"
    exit 1
  fi
  echo "Select a backup to restore:"
  select dir in "${backups[@]}"; do
    [ -n "$dir" ] || { msg "$RED" "Invalid selection"; exit 1; }
    msg "$BLUE" "Restoring from: $dir"
    [ -d "$dir/recordings" ] && cp -r "$dir/recordings" "$APP_DIR/" || msg "$YELLOW" "No recordings in backup."
    [ -d "$dir/gallery" ] && ensure_dir "$APP_DIR/app/static" && cp -r "$dir/gallery" "$APP_DIR/app/static/" || msg "$YELLOW" "No gallery in backup."
    msg "$GREEN" "Restore complete."
    break
  done
}

# --- Reclone (with backup prompt) ---
do_reclone() {
  msg "$YELLOW" "This will delete $APP_DIR. Back up first!"
  read -r -p "Backup before delete? (y/n): " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then do_backup; fi
  rm -rf "$APP_DIR"
  msg "$BLUE" "Cloning fresh repo from $REPO_URL..."
  git clone -b main "$REPO_URL" "$APP_DIR"
  ensure_venv
  msg "$GREEN" "Reclone complete."
}

# --- Run app (Flask) ---
run_local() {
  clone_if_missing
  ensure_venv
  git_update_notice
  msg "$GREEN" "Launching Flask app on port $PORT ($ENV)..."
  export FLASK_APP=run.py
  export FLASK_ENV="$ENV"
  flask run --host=0.0.0.0 --port="$PORT"
}

# --- Start with TLE update + recording ---
start_with_tle_and_recording() {
  clone_if_missing
  ensure_venv
  CFG_FILE="$APP_DIR/settings.json"
  if [ ! -f "$CFG_FILE" ]; then
    msg "$RED" "No settings.json found. Please configure location (latitude/longitude) first."
    exit 1
  fi
  LAT=$(jq -r '.latitude // empty' "$CFG_FILE")
  LON=$(jq -r '.longitude // empty' "$CFG_FILE")
  if [ -z "$LAT" ] || [ -z "$LON" ]; then
    msg "$RED" "Location not set in settings.json. Cannot start recording."
    exit 1
  fi

  msg "$GREEN" "Updating TLE data..."
  # shellcheck disable=SC1091
  source "$APP_DIR/venv/bin/activate"
  # Replace with the actual TLE update command used in your app:
  # If you have a CLI or Python module for this, call it here.
  # Example: python3 -m app.utils.tle_updater
  python3 - <<'PYCODE'
import sys, json, pathlib
from app.utils import tle as tle_utils, passes as passes_utils
from app import config_paths

cfg_file = pathlib.Path("settings.json")
if not cfg_file.exists():
    print("settings.json missing", file=sys.stderr); sys.exit(1)
cfg = json.load(open(cfg_file))
lat = cfg.get("latitude"); lon = cfg.get("longitude"); alt = cfg.get("altitude", 0)
tz = cfg.get("timezone", "UTC")

# Fetch/save TLEs (example mirrors your scheduler's approach)
data = []
for s in getattr(tle_utils, "TLE_SOURCES", []):
    if "ISS" in s.upper():
        t = tle_utils.fetch_tle(s)
        if t: data.append(t)
if data:
    tle_utils.save_tle(data)

# Generate next 24h predictions to the expected path
passes_utils.generate_predictions(lat, lon, alt, tz, "app/static/tle/active.txt")
print("TLE updated and predictions generated.")
PYCODE

  msg "$GREEN" "Starting scheduler/recording..."
  python3 app/utils/sdr_scheduler.py
}

# --- Admin menu ---
admin_menu() {
  while true; do
    echo "------ Admin Menu ------"
    echo "1) Pull latest changes (current branch)"
    echo "2) Switch branch"
    echo "3) Backup recordings/images"
    echo "4) Restore recordings/images"
    echo "5) Clear & reclone (with backup prompt)"
    echo "6) Back to main menu"
    read -r -p "Select an option: " choice
    case $choice in
      1) pull_update ;;
      2) read -r -p "Enter branch name: " br; switch_branch "$br" ;;
      3) do_backup ;;
      4) do_restore ;;
      5) do_reclone ;;
      6) break ;;
      *) msg "$RED" "Invalid choice" ;;
    esac
  done
}

# --- Interactive main menu ---
main_menu() {
  while true; do
    echo "=============================="
    echo "   SSTV Groundstation Launcher"
    echo "=============================="
    echo "1) Run local install"
    echo "2) Start (update TLE + recording)"
    echo "3) Admin options"
    echo "4) Exit"
    echo "=============================="
    read -r -p "Select an option: " choice
    case $choice in
      1) run_local ;;
      2) start_with_tle_and_recording ;;
      3) admin_menu ;;
      4) exit 0 ;;
      *) msg "$RED" "Invalid choice" ;;
    esac
  done
}

# --- Parse arguments ---
check_deps

run_flag=0; start_flag=0; update_flag=0; branch_arg=""
reclone_flag=0; backup_flag=0; restore_flag=0

# Support short and long options
while [[ $# -gt 0 ]]; do
  case "$1" in
    -r) run_flag=1; shift ;;
    -s) start_flag=1; shift ;;
    -u) update_flag=1; shift ;;
    -b) branch_arg="${2:-}"; shift 2 ;;
    --backup) backup_flag=1; shift ;;
    --restore) restore_flag=1; shift ;;
    --reclone) reclone_flag=1; shift ;;
    -p) PORT="${2:-5000}"; shift 2 ;;
    -e) ENV="${2:-development}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) msg "$RED" "Unknown option: $1"; usage; exit 1 ;;
  esac
done

# Execute based on flags or show menu
if [ "$run_flag" -eq 1 ]; then
  run_local; exit 0
fi
if [ "$start_flag" -eq 1 ]; then
  start_with_tle_and_recording; exit 0
fi
if [ "$update_flag" -eq 1 ]; then
  clone_if_missing; pull_update; exit 0
fi
if [ -n "$branch_arg" ]; then
  clone_if_missing; switch_branch "$branch_arg"; exit 0
fi
if [ "$backup_flag" -eq 1 ]; then
  do_backup; exit 0
fi
if [ "$restore_flag" -eq 1 ]; then
  do_restore; exit 0
fi
if [ "$reclone_flag" -eq 1 ]; then
  do_reclone; exit 0
fi

# No args: show interactive menu
main_menu
