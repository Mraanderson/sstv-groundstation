#!/bin/bash
# SSTV Groundstation Launcher (compact, branch-aware, status line)

set -euo pipefail
APP_DIR="$HOME/sstv-groundstation"
REPO_URL="https://github.com/Mraanderson/sstv-groundstation.git"
BACKUP_ROOT="$HOME/sstv-backups"
PORT="${PORT:-5000}" ENV="${ENV:-development}"
GREEN="\033[92m"; RED="\033[91m"; YELLOW="\033[93m"; RESET="\033[0m"
msg(){ echo -e "$1$2${RESET}"; }

# --- Helpers ---
have_repo(){ [ -d "$APP_DIR/.git" ]; }
json_get(){ grep -o "\"$1\"[[:space:]]*:[[:space:]]*[^,}]*" "$2" | sed 's/.*: *//;s/[",]//g'; }
status_line(){
  if ! have_repo; then
    echo -e "${RED}Install: none${RESET}"
  else
    cd "$APP_DIR"
    echo -e "${GREEN}Install: yes | Branch: $(git rev-parse --abbrev-ref HEAD)${RESET}"
  fi
}

# --- Git ---
pull_update(){ have_repo||{msg "$RED" "No install";return;}; cd "$APP_DIR"; git fetch origin; git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"; }
switch_branch(){
  have_repo||{msg "$RED" "No install";return;}
  cd "$APP_DIR"; git fetch --all --prune
  status_line
  mapfile -t b < <({ git branch --format='%(refname:short)'; git branch -r --format='%(refname:short)'|sed 's|origin/||'; } | sort -u)
  [ ${#b[@]} -eq 0 ] && { echo "No branches found."; return; }
  select br in "${b[@]}"; do
    [ -n "$br" ] && {
      git checkout "$br" 2>/dev/null || git checkout -b "$br" "origin/$br"
      git pull --ff-only origin "$br" || true
      status_line
      break
    }
  done
}

# --- Backup/restore ---
do_backup(){ mkdir -p "$BACKUP_ROOT"; d="$BACKUP_ROOT/$(date +%Y%m%d_%H%M%S)"; mkdir -p "$d"; [ -d "$APP_DIR/recordings" ]&&cp -r "$APP_DIR/recordings" "$d/"; [ -d "$APP_DIR/app/static/gallery" ]&&cp -r "$APP_DIR/app/static/gallery" "$d/"; msg "$GREEN" "Backup -> $d"; }
do_restore(){ shopt -s nullglob; b=("$BACKUP_ROOT"/*); shopt -u nullglob; [ ${#b[@]} -eq 0 ]&&{ msg "$RED" "No backups"; return; }; select d in "${b[@]}"; do [ -n "$d" ]&&{ cp -r "$d/recordings" "$APP_DIR/" 2>/dev/null||:; cp -r "$d/gallery" "$APP_DIR/app/static/" 2>/dev/null||:; msg "$GREEN" "Restored from $d"; break; }; done; }

# --- Reclone ---
do_reclone(){ read -rp "Backup before reclone? (y/n): " a; [[ $a =~ [Yy] ]]&&do_backup; [ -d "$APP_DIR" ]&&mv "$APP_DIR" "${APP_DIR}_old_$(date +%s)"; git clone -b main "$REPO_URL" "$APP_DIR"; ensure_venv; msg "$GREEN" "Fresh clone ready"; }

# --- Python env ---
ensure_venv(){ cd "$APP_DIR"; [ -d venv ]||python3 -m venv venv; source venv/bin/activate; [ -f requirements.txt ]&&pip install -q --upgrade pip -r requirements.txt; }

# --- Run modes ---
run_local(){ have_repo||{msg "$RED" "No install";return;}; ensure_venv; status_line; FLASK_APP=run.py FLASK_ENV=$ENV flask run --host=0.0.0.0 --port=$PORT; }
start_with_tle(){ have_repo||{msg "$RED" "No install";return;}; ensure_venv; f="$APP_DIR/settings.json"; [ -f "$f" ]||{ msg "$RED" "settings.json missing"; return; }; LAT=$(json_get latitude "$f"); LON=$(json_get longitude "$f"); [ -z "$LAT" -o -z "$LON" ]&&{ msg "$RED" "Location not set"; return; }; source "$APP_DIR/venv/bin/activate"; python3 -m app.utils.tle_updater||true; python3 app/utils/sdr_scheduler.py; }

# --- Menus ---
admin_menu(){ while :; do echo "---- Admin ----"; status_line; echo "1) Pull 2) Switch 3) Backup 4) Restore 5) Reclone 6) Back"; read -rp "> " c; case $c in 1)pull_update;;2)switch_branch;;3)do_backup;;4)do_restore;;5)do_reclone;;6)break;; esac; done; }
main_menu(){ while :; do echo "=== SSTV Launcher ==="; status_line; echo "1) Run 2) Start+TLE 3) Admin 4) Exit"; read -rp "> " c; case $c in 1)run_local;;2)start_with_tle;;3)admin_menu;;4)exit 0;; esac; done; }

# --- Args ---
while [[ $# -gt 0 ]]; do case $1 in
 -r)run_local;exit;; -s)start_with_tle;exit;; -u)pull_update;exit;;
 -b)switch_branch;exit;; --backup)do_backup;exit;; --restore)do_restore;exit;;
 --reclone)do_reclone;exit;; -p)PORT=$2;shift 2;; -e)ENV=$2;shift 2;;
 -h|--help)echo "Options: -r run -s start -u update -b switch --backup --restore --reclone";exit;;
 *)echo "Unknown $1";exit 1;; esac; done

main_menu
