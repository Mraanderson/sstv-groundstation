import json
import subprocess
import psutil
from pathlib import Path
from flask import render_template, send_file, abort, jsonify, request
from app.features.recordings import bp

RECORDINGS_DIR = Path("recordings")
SETTINGS_FILE = Path("settings.json")
SCHEDULER_SCRIPT = Path("app/utils/sdr_scheduler.py")

def load_settings():
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {"recording_enabled": False}

def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))

def find_scheduler_pid():
    """Find running scheduler process PID if any."""
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['cmdline'] and "sdr_scheduler.py" in " ".join(proc.info['cmdline']):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

@bp.route("/", methods=["GET"])
def recordings_list():
    """List all recordings with metadata for the web UI."""
    recordings = []
    for meta_file in RECORDINGS_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_file.read_text())
            base = meta_file.stem
            wav_file = RECORDINGS_DIR / f"{base}.wav"
            log_file = RECORDINGS_DIR / f"{base}.log"
            recordings.append({
                "base": base,
                "meta": meta,
                "wav_exists": wav_file.exists(),
                "log_exists": log_file.exists()
            })
        except Exception:
            continue
    recordings.sort(key=lambda r: r["meta"].get("timestamp", ""), reverse=True)
    return render_template("recordings/recordings.html", recordings=recordings)

@bp.route("/download/<filename>")
def download_recording(filename):
    """Download a recording file."""
    path = RECORDINGS_DIR / filename
    if path.exists():
        return send_file(path, as_attachment=True)
    abort(404)

@bp.route("/delete/<base>", methods=["POST"])
def delete_recording(base):
    """Delete a recording and its associated files."""
    for ext in [".wav", ".json", ".log"]:
        path = RECORDINGS_DIR / f"{base}{ext}"
        if path.exists():
            path.unlink()
    return jsonify({"status": "deleted"})

@bp.route("/enable", methods=["POST"])
def enable_recordings():
    """Enable recordings and start scheduler."""
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

    subprocess.Popen(["python3", str(SCHEDULER_SCRIPT)])
    return jsonify({"status": "enabled"}), 200

@bp.route("/disable", methods=["POST"])
def disable_recordings():
    """Disable recordings and stop scheduler."""
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

@bp.route("/status", methods=["GET"])
def recordings_status():
    """Return basic recording status for polling (used by passes page)."""
    settings = load_settings()
    pid = find_scheduler_pid()

    # Include last recording metadata if available
    last_meta = None
    meta_files = sorted(RECORDINGS_DIR.glob("*.json"), reverse=True)
    if meta_files:
        try:
            last_meta = json.loads(meta_files[0].read_text())
        except Exception:
            pass

    return jsonify({
        "recording_enabled": settings.get("recording_enabled", False),
        "recordings_count": len(list(RECORDINGS_DIR.glob("*.wav"))),
        "last_recording": last_meta,
        "scheduler_pid": pid
    })
    
