from flask import jsonify
from . import bp
import os
import json
from app.utils.passes import generate_predictions
from app import config_paths
from zoneinfo import ZoneInfo
from datetime import datetime

STATE_FILE = os.path.expanduser("~/sstv-groundstation/current_pass.json")

@bp.route("/timeline", methods=["GET"])
def pass_timeline():
    # Load config for location and timezone
    try:
        with open(config_paths.CONFIG_FILE) as f:
            cfg = json.load(f)
        lat = cfg.get("latitude")
        lon = cfg.get("longitude")
        alt = cfg.get("altitude", 0)
        tz = cfg.get("timezone", "UTC")
    except Exception:
        return jsonify({"error": "Could not load config"}), 500

    tle_path = "app/static/tle/active.txt"
    passes = generate_predictions(lat, lon, alt, tz, tle_path)
    now = datetime.now(ZoneInfo(tz))

    # Try to load current pass info
    current_pass = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                current_pass = json.load(f)
        except Exception:
            current_pass = None

    # Mark pass status for timeline
    timeline = []
    for p in passes:
        status = "upcoming"
        if p["start"] <= now <= p["end"]:
            status = "in_progress"
        elif p["end"] < now:
            status = "completed"
        timeline.append({
            "satellite": p["satellite"],
            "start": p["start"].isoformat(),
            "end": p["end"].isoformat(),
            "peak": p["peak"].isoformat(),
            "max_elevation": p["max_elevation"],
            "status": status
        })

    # Optionally, add current_pass if not in predictions
    return jsonify({
        "timeline": timeline,
        "current_pass": current_pass
    })
