#!/usr/bin/env bash
# SSTV Groundstation Unified Launcher (compact dashboard)

set -u
APP_DIR="$HOME/sstv-groundstation"
REPO_URL="https://github.com/Mraanderson/sstv-groundstation.git"
FILES_DIR="$HOME/sstv-files"
PORT="${PORT:-5000}" ENV="${ENV:-development}"
GREEN="\033[92m"; RED="\033[91m"; RESET="\033[0m"
msg(){ echo -e "$1$2${RESET}"; }
have_repo(){ [ -d "$APP_DIR/.git" ]; }

status_panel(){
  echo "╔════════════════════════════════════════╗"
  echo "║        Groundstation Status            ║"
  echo "╚════════════════════════════════════════╝"
  if have_repo; then
    branch=$(cd "$APP_DIR" && git rev-parse --abbrev-ref HEAD 2>/dev/null)
    msg "$GREEN" "Repo: ✔ Installed ($branch)"
  else
    msg "$RED" "Repo: ✘ Not installed"
  fi

  [ -d "$APP_DIR/venv" ] && msg "$GREEN" "Venv: ✔ Present" || msg "$RED" "Venv: ✘ Missing"

  local essentials_ok=1 missing=()
  for b in git python3 pip3 sox rtl_sdr ffmpeg; do
    command -v "$b" >/dev/null || { essentials_ok=0; missing+=("$b"); }
  done
  [ $essentials_ok -eq 1 ] && msg "$GREEN" "Essentials: ✔ All found" || msg "$RED" "Essentials: ✘ Missing (${missing[*]})"

  systemctl --user is-enabled sstv-groundstation >/dev/null 2>&1 && msg "$GREEN" "Systemd: ✔ Enabled" || msg "$RED" "Systemd: ✘ Not enabled"
  systemctl --user is-active --quiet sstv-groundstation && msg "$GREEN" "Service Status: ✔ Active" || msg "$RED" "Service Status: ✘ Inactive"

  # --- MODIFICATION START: Added TLE updater status ---
  systemctl --user is-enabled sstv-tle-updater.timer >/dev/null 2>&1 && msg "$GREEN" "TLE Updater: ✔ Enabled" || msg "$RED" "TLE Updater: ✘ Not enabled"
  systemctl --user is-active --quiet sstv-tle-updater.timer && msg "$GREEN" "TLE Timer:   ✔ Active" || msg "$RED" "TLE Timer:   ✘ Inactive"
  # --- MODIFICATION END ---

  if command -v rtl_test >/dev/null 2>&1; then
    rtl_test -t 2>&1 | grep -q "Found" && msg "$GREEN" "USB SDR: ✔ Detected" || msg "$RED" "USB SDR: ✘ Not detected"
  else
    msg "$RED" "USB SDR: ✘ rtl_test missing"
  fi

  if [ -x "$APP_DIR/launcher.sh" ]; then
    msg "$GREEN" "Launcher: ✔ Executable"
  elif [ -f "$APP_DIR/launcher.sh" ]; then
    msg "$RED" "Launcher: ✘ Not executable (chmod +x needed)"
  else
    msg "$RED" "Launcher: ✘ Missing"
  fi

  echo
}

install_essentials(){
  echo "Essentials: git python3 python3-pip sox rtl-sdr ffmpeg"
  if command -v apt >/dev/null; then cmd="sudo apt update && sudo apt install -y git python3 python3-pip sox rtl-sdr ffmpeg"
  elif command -v dnf >/dev/null; then cmd="sudo dnf install -y git python3 python3-pip sox rtl-sdr ffmpeg"
  else msg "$RED" "Unsupported pkg mgr"; return; fi
  echo "Dry run: $cmd"; read -p "Proceed? (y/n): " a; [[ "$a" =~ ^[Yy]$ ]]&&eval "$cmd"||msg "$RED" "Cancelled"
  echo "⚠ Blacklist DVB drivers for rtl-sdr in /etc/modprobe.d/blacklist-rtl.conf"
  echo -e "blacklist dvb_usb_rtl28xxu\nblacklist rtl2832\nblacklist rtl2830"
}

pull_update(){
  if ! have_repo; then
    msg "$RED" "No repo found."
    return
  fi

  branch=$(cd "$APP_DIR" && git rev-parse --abbrev-ref HEAD)
  msg "$GREEN" "Updating branch: $branch"

  # Check if the systemd service is installed
  if systemctl --user list-unit-files | grep -q '^sstv-groundstation.service'; then
    if systemctl --user is-active --quiet sstv-groundstation; then
      msg "$RED" "Stopping systemd service..."
      systemctl --user stop sstv-groundstation
      msg "$GREEN" "Service stopped."
    else
      msg "$GREEN" "Service already stopped."
    fi
  else
    msg "$RED" "Systemd service not installed. Skipping stop/restart."
  fi

  cd "$APP_DIR"
  msg "$GREEN" "Fetching latest changes..."
  git fetch origin

  msg "$GREEN" "Pulling updates..."
  git pull --ff-only origin "$branch"

  # Restart only if the service is installed
  if systemctl --user list-unit-files | grep -q '^sstv-groundstation.service'; then
    msg "$GREEN" "Restarting systemd service..."
    systemctl --user start sstv-groundstation
    msg "$GREEN" "Service restarted."
  fi
}

switch_branch(){
  have_repo||{ msg "$RED" "No repo"; return; }
  cd "$APP_DIR"; git fetch --all --prune
  mapfile -t b < <({ git branch --format='%(refname:short)'; git branch -r --format='%(refname:short)'|sed 's|origin/||'; }|sort -u)
  select br in "${b[@]}"; do
    [ -n "$br" ]||continue
    git checkout "$br"||git checkout -b "$br" "origin/$br"
    git pull --ff-only origin "$br"||true
    break
  done
}

do_backup(){
  mkdir -p "$FILES_DIR"
  [ -d "$APP_DIR/images" ]&&cp -r "$APP_DIR/images" "$FILES_DIR/"
  [ -d "$APP_DIR/recordings" ]&&cp -r "$APP_DIR/recordings" "$FILES_DIR/"
  msg "$GREEN" "Backup -> $FILES_DIR"
}

do_restore(){
  [ ! -d "$FILES_DIR" ]&&{ msg "$RED" "No backup"; return; }
  [ -d "$FILES_DIR/images" ]&&cp -r "$FILES_DIR/images" "$APP_DIR/"
  [ -d "$FILES_DIR/recordings" ]&&cp -r "$FILES_DIR/recordings" "$APP_DIR/"
  msg "$GREEN" "Restore complete"
}

remove_repo(){
  echo "WARNING: delete $APP_DIR"
  read -p "Are you sure? (yes/no): " a
  [ "$a" = "yes" ]&&rm -rf "$APP_DIR"&&echo "Repo removed."||echo "Cancelled."
}

ensure_venv(){
  cd "$APP_DIR"
  [ -d venv ]||python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  [ -f requirements.txt ]&&pip install -r requirements.txt
  [ -d sstv ]&&pip install ./sstv
}

run_local(){
  have_repo||{ msg "$RED" "No repo"; return; }
  ensure_venv
  branch=$(cd "$APP_DIR"&&git rev-parse --abbrev-ref HEAD)
  echo "Launching Flask ($branch) on port $PORT..."
  trap "deactivate 2>/dev/null; echo 'Exited cleanly.'" EXIT
  FLASK_APP=run.py FLASK_ENV=$ENV flask run --host=0.0.0.0 --port=$PORT
}

install_systemd_service(){
  d="$HOME/.config/systemd/user"; mkdir -p "$d"
  f="$d/sstv-groundstation.service"
  cat >"$f"<<EOF
[Unit]
Description=SSTV Groundstation
After=network.target
[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/launcher.sh -r
Restart=on-failure
Environment=FLASK_APP=run.py
Environment=FLASK_ENV=$ENV
[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable sstv-groundstation
  msg "$GREEN" "Systemd service enabled."
}

remove_systemd_service(){
  systemctl --user disable sstv-groundstation 2>/dev/null
  rm -f "$HOME/.config/systemd/user/sstv-groundstation.service"
  msg "$RED" "Systemd service removed."
}

# --- MODIFICATION START: Added TLE service management functions ---
install_tle_updater_service(){
  local systemd_dir="$HOME/.config/systemd/user"
  mkdir -p "$systemd_dir"
  
  local service_file="$systemd_dir/sstv-tle-updater.service"
  local timer_file="$systemd_dir/sstv-tle-updater.timer"

  msg "$GREEN" "Creating TLE updater systemd service..."
  cat >"$service_file"<<EOF
[Unit]
Description=TLE Updater for SSTV Groundstation

[Service]
Type=oneshot
# Use the python from the virtualenv and point to the script in app/utils
ExecStart=$APP_DIR/venv/bin/python3 $APP_DIR/app/utils/update_tles.py
Environment="SSTV_APP_DIR=$APP_DIR"
EOF

  msg "$GREEN" "Creating TLE updater systemd timer (12-hour interval)..."
  cat >"$timer_file"<<EOF
[Unit]
Description=Run TLE updater every 12 hours

[Timer]
# Run 5 minutes after boot, and every 12 hours thereafter
OnBootSec=5min
OnUnitActiveSec=12h
Unit=sstv-tle-updater.service

[Install]
WantedBy=timers.target
EOF

  systemctl --user daemon-reload
  systemctl --user enable --now sstv-tle-updater.timer
  msg "$GREEN" "TLE updater timer enabled and started."
  msg "$GREEN" "An initial TLE fetch will run in a few moments."
}

remove_tle_updater_service(){
  systemctl --user disable --now sstv-tle-updater.timer 2>/dev/null
  rm -f "$HOME/.config/systemd/user/sstv-tle-updater.service"
  rm -f "$HOME/.config/systemd/user/sstv-tle-updater.timer"
  systemctl --user daemon-reload
  msg "$RED" "TLE updater service and timer removed."
}
# --- MODIFICATION END ---

manage_boot(){
  while :; do
    clear
    # --- MODIFICATION START: Updated menu for clarity and new options ---
    echo "╔════════════════════════════════╗"
    echo "║   Boot & Service Options       ║"
    echo "╚════════════════════════════════╝"
    echo "--- Main Application ---"
    echo " 1) Enable web app service"
    echo " 2) Disable web app service"
    echo " 3) Update code & restart web app"
    echo
    echo "--- TLE Updater ---"
    echo " 4) Enable TLE updater (12hr)"
    echo " 5) Disable TLE updater"
    echo
    echo " 9) Back"
    read -rp "> " c
    case $c in
      1) install_systemd_service;;
      2) remove_systemd_service;;
      3) pull_update;;
      4) install_tle_updater_service;;
      5) remove_tle_updater_service;;
      9) break;;
      *) echo "Invalid option";;
    esac
    # --- MODIFICATION END ---
    read -rp "Press Enter..."
  done
}

ensure_update_script(){
  local script="$APP_DIR/update-service.sh"
  if [ ! -f "$script" ]; then
    cat >"$script"<<EOF
#!/usr/bin/env bash
APP_DIR="\$HOME/sstv-groundstation"
GREEN="\\033[92m"; RED="\\033[91m"; RESET="\\033[0m"
msg(){ echo -e "\$1\$2\${RESET}"; }

branch=\$(cd "\$APP_DIR" && git rev-parse --abbrev-ref HEAD)
msg "\$GREEN" "Updating branch: \$branch"

if systemctl --user is-active --quiet sstv-groundstation; then
  msg "\$RED" "Stopping service..."
  systemctl --user stop sstv-groundstation
  msg "\$GREEN" "Service stopped."
fi

cd "\$APP_DIR"
git fetch origin && git pull --ff-only origin "\$branch"
msg "\$GREEN" "Pulled latest changes."

msg "\$GREEN" "Restarting service..."
systemctl --user start sstv-groundstation
msg "\$GREEN" "Service restarted."
EOF
    chmod +x "$script"
    msg "$GREEN" "Created and made update-service.sh executable."
  fi
}

main_menu(){
  while :; do
    clear
    status_panel
    if ! have_repo; then
      echo "1) Clone main branch"
      echo "2) Exit"
      read -rp "> " c
      case $c in
        1) git clone -b main "$REPO_URL" "$APP_DIR";;
        2) exit 0;;
      esac
    else
      branch=$(cd "$APP_DIR"&&git rev-parse --abbrev-ref HEAD)
      echo "1) Run web app ($branch)"
      echo "2) Pull latest"
      echo "3) Switch branch"
      echo "4) Backup"
      echo "5) Restore"
      echo "6) Remove repo"
      echo "7) Install essentials"
      echo "8) Run at boot"
      echo "0) Exit"
      read -rp "> " c
      case $c in
        1) run_local;;
        2) pull_update;;
        3) switch_branch;;
        4) do_backup;;
        5) do_restore;;
        6) remove_repo;;
        7) install_essentials;;
        8) manage_boot;;
        0) exit 0;;
        *) echo "Invalid option"; sleep 1;;
      esac
    fi
  done
}

# --- Entry point ---
if [[ "${1:-}" == "-r" ]]; then
  run_local
else
  main_menu
fi
