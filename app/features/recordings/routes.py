
import json
import subprocess
import psutil
import os
from pathlib import Path
from flask import render_template, jsonify, send_from_directory, request
from werkzeug.utils import secure_filename

from app.features.recordings import bp
import app.utils.tle as tle_utils
import app.utils.passes as passes_utils
from app.utils.decoder import process_uploaded_wav
from app import config_paths

# ✅ Always resolve to the top-level recordings directory, regardless of CWD
RECORDINGS_DIR = (Path(__file__).resolve().parent.parent.parent.parent / "recordings").resolve()
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
    tz = config_data.get("timezone", "UTC")
    tle_path = "app/static/tle/active.txt"

    passes_utils.generate_predictions(lat, lon, alt, tz, tle_path)
    print("📅 Pass predictions updated for next 24h.")


def build_recordings_list():
    """Helper to collect recordings with metadata."""
    recordings = []
    for meta_file in RECORDINGS_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_file.read_text())
            base = meta_file.stem
            wav_file = next(RECORDINGS_DIR.glob(f"{base}*.wav"), None)
            png_file = next(RECORDINGS_DIR.glob(f"{base}*.png"), None)

            recordings.append({
                "base": base,
                "meta": meta,
                "wav_file": wav_file,
                "png_file": png_file,
                "json_file": meta_file
            })
        except Exception:
            continue

    recordings.sort(key=lambda r: r["meta"].get("timestamp", ""), reverse=True)
    return recordings


def recordings_list_with_status(status=None):
    """Render recordings page with optional status alert."""
    recordings = build_recordings_list()
    return render_template(
        "recordings/recordings.html",
        recordings=recordings,
        rec_dir=RECORDINGS_DIR,
        status=status
    )


@bp.route("/", methods=["GET"])
def recordings_list():
    return recordings_list_with_status()


@bp.route("/delete", methods=["POST"])
def delete_recording():
    base = request.form.get("base")
    if base:
        for f in RECORDINGS_DIR.glob(f"{base}*"):
            if f.is_file():
                f.unlink()
    return recordings_list()


@bp.route("/bulk-delete", methods=["POST"])
def bulk_delete():
    bases = request.form.getlist("bases")
    for base in bases:
        for f in RECORDINGS_DIR.glob(f"{base}*"):
            if f.is_file():
                f.unlink()
    return recordings_list()


@bp.route("/files/<path:filename>")
def recordings_file(filename):
    return send_from_directory(RECORDINGS_DIR, filename, as_attachment=False)


@bp.route("/enable", methods=["POST"])
def enable_recordings():
    settings = load_settings()
    if settings.get("recording_enabled"):
        return jsonify({"status": "already enabled"}), 200

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] in ('rtl_fm', 'sox'):
                proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    settings["recording_enabled"] = True
    save_settings(settings)

    refresh_tle_and_predictions()
    subprocess.Popen(["python3", "-m", "app.utils.sdr_scheduler"])

    return jsonify({"status": "enabled"}), 200


@bp.route("/disable", methods=["POST"])
def disable_recordings():
    settings = load_settings()
    settings["recording_enabled"] = False
    save_settings(settings)

    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['cmdline'] and "app.utils.sdr_scheduler" in " ".join(proc.info['cmdline']):
                proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return jsonify({"status": "disabled"}), 200


@bp.route("/status", methods=["GET"])
def recordings_status():
    settings = load_settings()
    enabled = settings.get("recording_enabled", False)

    scheduler_pid = None
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['cmdline'] and "app.utils.sdr_scheduler" in " ".join(proc.info['cmdline']):
                scheduler_pid = proc.info['pid']
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if scheduler_pid is None:
        enabled = False
        settings["recording_enabled"] = False
        save_settings(settings)

    return jsonify({
        "recording_enabled": enabled,
        "scheduler_pid": scheduler_pid
    })


@bp.route("/upload", methods=["POST"])
def upload_wav():
    """Handle user-uploaded WAV files for SSTV decoding."""
    file = request.files.get("wav_file")
    if not file or not file.filename.endswith(".wav"):
        return recordings_list_with_status({
            "success": False,
            "error": "Invalid file format. Please upload a .wav file."
        })

    filename = secure_filename(file.filename)
    save_path = RECORDINGS_DIR / filename
    file.save(save_path)

    try:
        # Run your decoder
        result = process_uploaded_wav(save_path)

        # Calculate file size in MB
        file_mb = None
        try:
            file_mb = round(os.path.getsize(save_path) / (1024 * 1024), 2)
        except Exception:
            file_mb = None

        # Expecting process_uploaded_wav to return dict with file paths
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
        return recordings_list_with_status({
            "success": False,
            "error": f"Decoding failed: {e}"
        })
        
