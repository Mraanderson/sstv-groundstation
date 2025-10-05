#!/bin/bash
# SSTV Groundstation Unified Launcher

set -u   # safer than -euo pipefail (won’t silently kill script)
APP_DIR="$HOME/sstv-groundstation"
REPO_URL="https://github.com/Mraanderson/sstv-groundstation.git"
FILES_DIR="$HOME/sstv-files"
PORT="${PORT:-5000}" ENV="${ENV:-development}"
GREEN="\033[92m"; RED="\033[91m"; RESET="\033[0m"

msg(){ echo -e "$1$2${RESET}"; }
have_repo(){ [ -d "$APP_DIR/.git" ]; }

# --- System requirements check ---
check_requirements() {
  echo "Checking system requirements..."
  local missing=0
  for bin in sox rtl_sdr; do
    if command -v "$bin" >/dev/null 2>&1; then
      msg "$GREEN" "✔ $bin found: $(command -v $bin)"
    else
      msg "$RED" "✘ $bin NOT found"
      missing=1
    fi
  done
  [ $missing -eq 1 ] && msg "$RED" "Some required system binaries are missing."
}

# --- Git helpers ---
pull_update(){
  have_repo || { msg "$RED" "No repo installed"; return; }
  cd "$APP_DIR"
  echo "Pulling latest changes..."
  git fetch origin
  git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"
}

switch_branch(){
  have_repo || { msg "$RED" "No repo installed"; return; }
  cd "$APP_DIR"; git fetch --all --prune
  echo "Available branches:"
  mapfile -t b < <({ git branch --format='%(refname:short)'; git branch -r --format='%(refname:short)'|sed 's|origin/||'; }|sort -u)
  select br in "${b[@]}"; do
    [ -n "$br" ] || continue
    git checkout "$br" || git checkout -b "$br" "origin/$br"
    git pull --ff-only origin "$br" || true
    echo "Now on branch: $(git rev-parse --abbrev-ref HEAD)"
    break
  done
}

# --- Backup/restore ---
do_backup(){
  mkdir -p "$FILES_DIR"
  [ -d "$APP_DIR/images" ] && cp -r "$APP_DIR/images" "$FILES_DIR/"
  [ -d "$APP_DIR/recordings" ] && cp -r "$APP_DIR/recordings" "$FILES_DIR/"
  msg "$GREEN" "Backup complete -> $FILES_DIR"
}
do_restore(){
  [ ! -d "$FILES_DIR" ] && { msg "$RED" "No backup folder at $FILES_DIR"; return; }
  [ -d "$FILES_DIR/images" ] && cp -r "$FILES_DIR/images" "$APP_DIR/"
  [ -d "$FILES_DIR/recordings" ] && cp -r "$FILES_DIR/recordings" "$APP_DIR/"
  msg "$GREEN" "Restore complete from $FILES_DIR"
}

# --- Remove repo (with warnings) ---
remove_repo(){
  echo "WARNING: This will delete $APP_DIR and all its contents."
  echo "Images and recordings will be lost unless you back them up."
  read -p "Are you sure? (yes/no): " ans
  [ "$ans" = "yes" ] && rm -rf "$APP_DIR" && echo "Repository removed." || echo "Cancelled."
}

# --- Python env ---
ensure_venv(){
  cd "$APP_DIR"
  [ -d venv ] || { echo "Creating virtual environment..."; python3 -m venv venv; }
  echo "Activating virtual environment..."
  source venv/bin/activate
  pip install --upgrade pip
  [ -f requirements.txt ] && pip install -r requirements.txt
  [ -d sstv ] && pip install ./sstv
}

# --- Run mode ---
run_local(){
  have_repo || { msg "$RED" "No repo installed"; return; }
  ensure_venv
  check_requirements
  echo "Launching Flask app on port $PORT..."
  trap "deactivate 2>/dev/null; echo 'Exited cleanly.'" EXIT
  FLASK_APP=run.py FLASK_ENV=$ENV flask run --host=0.0.0.0 --port=$PORT
}

# --- Menu ---
main_menu(){
  while :; do
    clear
    cat <<'EOF'
  +---------------------------+
  |   SSTV Groundstation App  |
  +---------------------------+
EOF
    if ! have_repo; then
      echo "1) Clone main branch"
      echo "2) Exit"
      read -rp "> " c
      case $c in
        1) git clone -b main "$REPO_URL" "$APP_DIR";;
        2) exit 0;;
      esac
    else
      echo "1) Run web app"
      echo "2) Pull latest"
      echo "3) Switch branch"
      echo "4) Backup (images + recordings)"
      echo "5) Restore (from backup)"
      echo "6) Remove repo (with warnings)"
      echo "7) Exit"
      read -rp "> " c
      case $c in
        1) run_local;;
        2) pull_update;;
        3) switch_branch;;
        4) do_backup;;
        5) do_restore;;
        6) remove_repo;;
        7) exit 0;;
      esac
    fi
  done
}

main_menu