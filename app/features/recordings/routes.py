import json
from pathlib import Path
from flask import render_template, send_file, abort, jsonify, request

RECORDINGS_DIR = Path("recordings")
SETTINGS_FILE = Path("settings.json")

from app.features.recordings import bp

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
    # Sort newest first
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

@bp.route("/status", methods=["GET"])
def recordings_status():
    """Return basic recording status for polling (used by passes page)."""
    recording_enabled = False
    if SETTINGS_FILE.exists():
        try:
            recording_enabled = json.loads(SETTINGS_FILE.read_text()).get("recording_enabled", False)
        except Exception:
            pass

    # Include last recording metadata if available
    last_meta = None
    meta_files = sorted(RECORDINGS_DIR.glob("*.json"), reverse=True)
    if meta_files:
        try:
            last_meta = json.loads(meta_files[0].read_text())
        except Exception:
            pass

    return jsonify({
        "recording_enabled": recording_enabled,
        "recordings_count": len(list(RECORDINGS_DIR.glob("*.wav"))),
        "last_recording": last_meta
    })

@bp.route("/enable", methods=["POST"])
def recordings_enable():
    """Enable or disable recordings via web UI."""
    data = request.get_json(silent=True) or {}
    enable = bool(data.get("enable", True))

    try:
        settings = {}
        if SETTINGS_FILE.exists():
            settings = json.loads(SETTINGS_FILE.read_text())
        settings["recording_enabled"] = enable
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
        return jsonify({"status": "ok", "recording_enabled": enable})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
