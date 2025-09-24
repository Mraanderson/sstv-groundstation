import json
import subprocess
import psutil
import os
from pathlib import Path
from flask import render_template, send_file, abort, jsonify

# ✅ import the Blueprint defined in __init__.py
from app.features.recordings import bp

# utility imports
import app.utils.tle as tle_utils
import app.utils.passes as passes_utils
from app import config_paths   # for user_config.json

RECORDINGS_DIR = Path("recordings")
SETTINGS_FILE = Path("settings.json")

def load_settings():
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {"recording_enabled": False}

def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))

def load_config_data():
    if os.path.exists(config_paths.CONFIG_FILE):
        with open(config_paths.CONFIG_FILE) as f:
            return json.load(f)
    return {}

def refresh_tle_and_predictions():
    """Fetch latest TLEs and regenerate pass predictions."""
    config_data = load_config_data()
    if not config_data.get("latitude") or not config_data.get("longitude"):
        print("⚠ No location set — skipping TLE refresh.")
        return

    tle_data = []
    for sat_name in tle_utils.TLE_SOURCES.keys():
        tle = tle_utils.fetch_tle(sat_name)
        if tle:
            tle_data.append(tle)
            print(f"✅ Fetched TLE for {sat_name}")
        else:
            print(f"⚠ No TLE found for {sat_name}")

    tle_utils.save_tle(tle_data)

    lat = config_data["latitude"]
    lon = config_data["longitude"]
    alt = config_data.get("altitude", 0)
    tz  = config_data.get("timezone", "UTC")
    tle_path = "app/static/tle/active.txt"

    passes_utils.generate_predictions(lat, lon, alt, tz, tle_path)
    print("📅 Pass predictions updated for next 24h.")

@bp.route("/", methods=["GET"])
def recordings_list():
    """List all recordings with metadata for the web UI."""
    recordings = []
    for meta_file in RECORDINGS_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_file.read_text())
            base = meta_file.stem
            recordings.append({
                "base": base,
                "meta": meta,
                "wav_exists": (RECORDINGS_DIR / f"{base}.wav").exists(),
                "log_exists": (RECORDINGS_DIR / f"{base}.log").exists()
            })
        except Exception:
            continue
    recordings.sort(key=lambda r: r["meta"].get("timestamp", ""), reverse=True)
    return render_template("recordings/recordings.html", recordings=recordings)

@bp.route("/enable", methods=["POST"])
def enable_recordings():
    """Enable recordings, refresh TLE, and start scheduler."""
    settings = load_settings()
    if settings.get("recording_enabled"):
        return jsonify({"status": "already enabled"}), 200

    # Kill stray SDR processes before starting scheduler
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] in ('rtl_fm', 'sox'):
                proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    settings["recording_enabled"] = True
    save_settings(settings)

    # Refresh TLE and predictions before starting scheduler
    refresh_tle_and_predictions()

    # ✅ Run scheduler as a module so imports work
    subprocess.Popen(["python3", "-m", "app.utils.sdr_scheduler"])

    return jsonify({"status": "enabled"}), 200
    
