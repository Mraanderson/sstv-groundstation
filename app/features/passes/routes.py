import os
from datetime import datetime, timedelta, timezone
from flask import render_template, current_app, jsonify
from zoneinfo import ZoneInfo
import requests

from . import bp
from app.utils.sdr import rtl_sdr_present
from app.utils import passes  # <-- import the shared utility

SSTV_SATELLITES = [
    {
        "name": "ISS (ZARYA)",
        "norad_id": 25544,
        "frequency": "145.800",
        "status": "Active",
        "notes": "ARISS SSTV events"
    }
]

def tle_file_path():
    return os.path.join(current_app.config["TLE_DIR"], "active.txt")

def get_tle_age_days(tle_path):
    """Return age of TLE file in days, or None if it can't be determined."""
    try:
        with open(tle_path) as f:
            lines = [line.strip() for line in f if line.strip()]
        if len(lines) < 2:
            return None
        line1 = lines[1]
        epoch_str = line1[18:32]  # YYDDD.DDDDDDDD
        year = int(epoch_str[:2])
        year += 2000 if year < 57 else 1900
        day_of_year = float(epoch_str[2:])
        epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)
        return (datetime.now(timezone.utc) - epoch).total_seconds() / 86400
    except Exception:
        return None

@bp.route("/", endpoint="passes_page")
def passes_page():
    lat = current_app.config.get("LATITUDE")
    lon = current_app.config.get("LONGITUDE")
    alt = current_app.config.get("ALTITUDE_M")
    tz = current_app.config.get("TIMEZONE")
    tle_path = tle_file_path()
    sdr_flag = rtl_sdr_present()

    tle_info = None
    if os.path.exists(tle_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(tle_path))
        tle_info = {
            "filename": os.path.basename(tle_path),
            "last_updated": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            "age_days": get_tle_age_days(tle_path)
        }

    passes_list = passes.generate_predictions(lat, lon, alt, tz, tle_path)
    now_for_template = datetime.now(ZoneInfo(tz)) if tz else datetime.now()

    return render_template(
        "passes/passes.html",
        tle_info=tle_info,
        satellites=[s["name"] for s in SSTV_SATELLITES],
        passes=passes_list,
        timezone=tz,
        now=now_for_template,
        location_set=None not in (lat, lon, alt, tz),
        sstv_sats=SSTV_SATELLITES,
        sdr_present=sdr_flag
    )

@bp.route("/update-tle", endpoint="update_tle")
def update_tle():
    try:
        tle_dir = current_app.config["TLE_DIR"]
        os.makedirs(tle_dir, exist_ok=True)
        path = tle_file_path()

        iss = SSTV_SATELLITES[0]
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={iss['norad_id']}&FORMAT=TLE"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        tle_lines = resp.text.strip().splitlines()

        if len(tle_lines) >= 3:
            with open(path, "w") as f:
                f.write("\n".join(tle_lines[:3]) + "\n")

        # Generate passes immediately after updating TLE
        lat = current_app.config.get("LATITUDE")
        lon = current_app.config.get("LONGITUDE")
        alt = current_app.config.get("ALTITUDE_M")
        tz = current_app.config.get("TIMEZONE")
        passes.generate_predictions(lat, lon, alt, tz, path)

        return jsonify({"status": "success", "updated": True})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
        
