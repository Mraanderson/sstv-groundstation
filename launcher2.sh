#!/usr/bin/env bash
# SSTV Groundstation Unified Launcher (compact)

set -u
APP_DIR="$HOME/sstv-groundstation"
REPO_URL="https://github.com/Mraanderson/sstv-groundstation.git"
FILES_DIR="$HOME/sstv-files"
PORT="${PORT:-5000}" ENV="${ENV:-development}"
GREEN="\033[92m"; RED="\033[91m"; RESET="\033[0m"
msg(){ echo -e "$1$2${RESET}"; }
have_repo(){ [ -d "$APP_DIR/.git" ]; }

status_line(){ 
  if ! have_repo; then msg "$RED" "Installed: no"; 
  else cd "$APP_DIR"; msg "$GREEN" "Installed: yes | Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"; fi; 
}

verify_essentials(){
  echo "Verifying required software..."; local missing=0
  for bin in git python3 pip3 sox rtl_sdr ffmpeg; do
    if command -v "$bin" >/dev/null; then
      case $bin in
        python3|git|pip3) ver=$($bin --version 2>&1) ;;
        sox) ver=$($bin --version|head -n1) ;;
        ffmpeg) ver=$($bin -version|head -n1) ;;
        rtl_sdr) ver=$($bin -V 2>&1|head -n1) ;;
      esac
      msg "$GREEN" "✔ $bin: $(command -v $bin) $ver"
    else msg "$RED" "✘ $bin NOT found"; missing=1; fi
  done
  [ $missing -eq 0 ] && msg "$GREEN" "All required tools installed." || msg "$RED" "Some required tools missing."
  read -rp "Press Enter to return..."
}

install_essentials(){
  echo "Essentials: git python3 python3-pip sox rtl-sdr ffmpeg"
  if command -v apt >/dev/null; then cmd="sudo apt update && sudo apt install -y git python3 python3-pip sox rtl-sdr ffmpeg"
  elif command -v dnf >/dev/null; then cmd="sudo dnf install -y git python3 python3-pip sox rtl-sdr ffmpeg"
  else msg "$RED" "Unsupported package manager."; return; fi
  echo "Dry run: $cmd"; read -p "Proceed? (y/n): " ans
  [[ "$ans" =~ ^[Yy]$ ]] && eval "$cmd" && verify_essentials || msg "$RED" "Installation cancelled."
  echo "⚠ Blacklist DVB drivers for rtl-sdr (/etc/modprobe.d/blacklist-rtl.conf):"
  echo -e "blacklist dvb_usb_rtl28xxu\nblacklist rtl2832\nblacklist rtl2830"
}

pull_update(){ have_repo || { msg "$RED" "No repo"; return; }; cd "$APP_DIR"; git fetch origin; git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"; }
switch_branch(){ have_repo || { msg "$RED" "No repo"; return; }; cd "$APP_DIR"; git fetch --all --prune; mapfile -t b < <({ git branch --format='%(refname:short)'; git branch -r --format='%(refname:short)'|sed 's|origin/||'; }|sort -u); select br in "${b[@]}"; do [ -n "$br" ]||continue; git checkout "$br"||git checkout -b "$br" "origin/$br"; git pull --ff-only origin "$br"||true; break; done; }
do_backup(){ mkdir -p "$FILES_DIR"; [ -d "$APP_DIR/images" ]&&cp -r "$APP_DIR/images" "$FILES_DIR/"; [ -d "$APP_DIR/recordings" ]&&cp -r "$APP_DIR/recordings" "$FILES_DIR/"; msg "$GREEN" "Backup -> $FILES_DIR"; }
do_restore(){ [ ! -d "$FILES_DIR" ]&&{ msg "$RED" "No backup"; return; }; [ -d "$FILES_DIR/images" ]&&cp -r "$FILES_DIR/images" "$APP_DIR/"; [ -d "$FILES_DIR/recordings" ]&&cp -r "$FILES_DIR/recordings" "$APP_DIR/"; msg "$GREEN" "Restore complete"; }
remove_repo(){ echo "WARNING: delete $APP_DIR"; read -p "Are you sure? (yes/no): " ans; [ "$ans" = "yes" ]&&rm -rf "$APP_DIR"&&echo "Repo removed."||echo "Cancelled."; }
ensure_venv(){ cd "$APP_DIR"; [ -d venv ]||python3 -m venv venv; source venv/bin/activate; pip install --upgrade pip; [ -f requirements.txt ]&&pip install -r requirements.txt; [ -d sstv ]&&pip install ./sstv; }
run_local(){ have_repo||{ msg "$RED" "No repo"; return; }; ensure_venv; verify_essentials; local branch=$(cd "$APP_DIR"&&git rev-parse --abbrev-ref HEAD); echo "Launching Flask ($branch) on port $PORT..."; trap "deactivate 2>/dev/null; echo 'Exited cleanly.'" EXIT; FLASK_APP=run.py FLASK_ENV=$ENV flask run --host=0.0.0.0 --port=$PORT; }

main_menu(){
  while :; do clear; echo -e "\n  +---------------------------+\n  |   SSTV Groundstation App  |\n  +---------------------------+"; status_line; echo
    if ! have_repo; then echo "1) Clone main branch"; echo "2) Exit"; read -rp "> " c; case $c in 1) git clone -b main "$REPO_URL" "$APP_DIR";; 2) exit 0;; esac
    else local branch=$(cd "$APP_DIR"&&git rev-parse --abbrev-ref HEAD)
      echo "1) Run web app (current: $branch)"; echo "2) Pull latest"; echo "3) Switch branch"; echo "4) Backup"; echo "5) Restore"; echo "6) Remove repo"; echo "7) Install essentials"; echo "8) Verify essentials"; echo "9) Exit"
      read -rp "> " c
      case $c in 1) run_local;; 2) pull_update;; 3) switch_branch;; 4) do_backup;; 5) do_restore;; 6) remove_repo;; 7) install_essentials;; 8) verify_essentials;; 9) exit 0;; esac
    fi
  done
}

main_menu