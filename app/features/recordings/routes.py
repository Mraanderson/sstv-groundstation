import os, json
from flask import render_template, send_file, abort, jsonify, request
from pathlib import Path

RECORDINGS_DIR = Path("recordings")

from app.features.recordings import bp

@bp.route("/", methods=["GET"])
def recordings_list():
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
    path = RECORDINGS_DIR / filename
    if path.exists():
        return send_file(path, as_attachment=True)
    abort(404)

@bp.route("/delete/<base>", methods=["POST"])
def delete_recording(base):
    for ext in [".wav", ".json", ".log"]:
        path = RECORDINGS_DIR / f"{base}{ext}"
        if path.exists():
            path.unlink()
    return jsonify({"status": "deleted"})
  
