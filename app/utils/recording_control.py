from flask import Blueprint, jsonify
import json
import subprocess
import psutil
from pathlib import Path

recordings_bp = Blueprint('recordings', __name__)

SETTINGS_FILE = Path("settings.json")
SCHEDULER_SCRIPT = Path("app/utils/sdr_scheduler.py")

def load_settings():
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {"recording_enabled": False}

def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings))

def find_scheduler_pid():
    """Find running scheduler process PID if any."""
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['cmdline'] and "sdr_scheduler.py" in " ".join(proc.info['cmdline']):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

@recordings_bp.route("/enable", methods=["POST"])
def enable_recordings():
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

    subprocess.Popen(["python", str(SCHEDULER_SCRIPT)])
    return jsonify({"status": "enabled"}), 200

@recordings_bp.route("/disable", methods=["POST"])
def disable_recordings():
    settings = load_settings()
    if not settings.get("recording_enabled"):
        return jsonify({"status": "already disabled"}), 200

    settings["recording_enabled"] = False
    save_settings(settings)

    pid = find_scheduler_pid()
    if pid:
        psutil.Process(pid).terminate()
        return jsonify({"status": "disabled", "pid": pid}), 200
    return jsonify({"status": "disabled", "pid": None}), 200

@recordings_bp.route("/status", methods=["GET"])
def status():
    settings = load_settings()
    pid = find_scheduler_pid()
    return jsonify({
        "recording_enabled": settings.get("recording_enabled", False),
        "scheduler_pid": pid
    })
    
