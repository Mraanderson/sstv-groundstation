# recordings/routes.py

import json
import subprocess
import psutil
import os
from pathlib import Path
from flask import Blueprint, render_template, jsonify, send_from_directory, request
from werkzeug.utils import secure_filename

from app.utils.decoder import process_uploaded_wav
import app.utils.tle as tle_utils
import app.utils.passes as passes_utils
from app import config_paths

# IMPORTANT: blueprint name must be 'recordings'
bp = Blueprint("recordings", __name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RECORDINGS_DIR = (BASE_DIR / "recordings").resolve()
SETTINGS_FILE = Path("settings.json")
SCHEDULER_SCRIPT = Path("app/utils/sdr_scheduler.py")

def build_recordings_lists():
    iss_recordings = []
    other_files = []

    for meta_file in RECORDINGS_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_file.read_text())
            base = meta_file.stem
            wav_file = next(RECORDINGS_DIR.glob(f"{base}*.wav"), None)
            png_file = next(RECORDINGS_DIR.glob(f"{base}*.png"), None)
            log_file = next(RECORDINGS_DIR.glob(f"{base}*.log"), None)

            iss_recordings.append({
                "base": base,
                "meta": meta,
                "wav_file": wav_file,
                "png_file": png_file,
                "log_file": log_file,
                "json_file": meta_file
            })
        except Exception:
            continue

    all_files = set(RECORDINGS_DIR.glob("*"))
    used_files = {r["wav_file"] for r in iss_recordings if r["wav_file"]} \
               | {r["png_file"] for r in iss_recordings if r["png_file"]} \
               | {r["json_file"] for r in iss_recordings if r["json_file"]} \
               | {r["log_file"] for r in iss_recordings if r["log_file"]}

    for f in all_files - used_files:
        if f.is_file():
            other_files.append(f)

    iss_recordings.sort(key=lambda r: r["meta"].get("timestamp", ""), reverse=True)
    other_files.sort(key=lambda f: f.name)
    return iss_recordings, other_files

def load_settings():
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return {"recording_enabled": False}

def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))

def find_scheduler_pid():
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            if proc.info["cmdline"] and "sdr_scheduler.py" in " ".join(proc.info["cmdline"]):
                return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def recordings_list_with_status(status=None):
    iss_recordings, other_files = build_recordings_lists()
    return render_template(
        "recordings/recordings.html",
        iss_recordings=iss_recordings,
        other_files=other_files,
        rec_dir=RECORDINGS_DIR,
        status=status
    )

# Routes

@bp.route("/", methods=["GET"])
def recordings_list():
    return recordings_list_with_status()

@bp.route("/files/<path:filename>")
def recordings_file(filename):
    return send_from_directory(RECORDINGS_DIR, filename, as_attachment=False)

@bp.route("/upload", methods=["POST"])
def upload_wav():
    file = request.files.get("wav_file")
    if not file or not file.filename.endswith(".wav"):
        return recordings_list_with_status({"success": False, "error": "Invalid file format. Please upload a .wav file."})

    filename = secure_filename(file.filename)
    save_path = RECORDINGS_DIR / filename
    file.save(save_path)

    try:
        result = process_uploaded_wav(save_path)
        file_mb = round(os.path.getsize(save_path) / (1024 * 1024), 2)
        status = {
            "success": True,
            "wav_name": filename,
            "file_mb": file_mb,
            "png_name": result.get("png_file") if isinstance(result, dict) else None,
            "json_name": result.get("json_file") if isinstance(result, dict) else None,
            "log_name": result.get("log_file") if isinstance(result, dict) else None
        }
        return recordings_list_with_status(status)
    except Exception as e:
        return recordings_list_with_status({"success": False, "error": f"Decoding failed: {e}"})

@bp.route("/delete-file", methods=["POST"])
def delete_file():
    filename = request.form.get("filename")
    if filename:
        target = RECORDINGS_DIR / filename
        if target.exists():
            target.unlink()
    return recordings_list()

@bp.route("/rename-file", methods=["POST"])
def rename_file():
    old = request.form.get("old_name")
    new = request.form.get("new_name")
    if old and new:
        old_path = RECORDINGS_DIR / old
        new_path = RECORDINGS_DIR / secure_filename(new)
        if old_path.exists():
            old_path.rename(new_path)
    return recordings_list()

# Scheduler control

@bp.route("/enable", methods=["POST"])
def enable_recordings():
    settings = load_settings()
    if settings.get("recording_enabled"):
        return jsonify({"status": "already enabled"}), 200

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["name"] in ("rtl_fm", "sox"):
                proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    settings["recording_enabled"] = True
    save_settings(settings)
    subprocess.Popen(["python3", str(SCHEDULER_SCRIPT)])
    return jsonify({"status": "enabled"}), 200

@bp.route("/disable", methods=["POST"])
def disable_recordings():
    settings = load_settings()
    settings["recording_enabled"] = False
    save_settings(settings)

    pid = find_scheduler_pid()
    if pid:
        psutil.Process(pid).terminate()
        return jsonify({"status": "disabled", "pid": pid}), 200
    return jsonify({"status": "disabled", "pid": None}), 200

@bp.route("/status", methods=["GET"])
def recordings_status():
    settings = load_settings()
    pid = find_scheduler_pid()
    return jsonify({"recording_enabled": settings.get("recording_enabled", False), "scheduler_pid": pid})