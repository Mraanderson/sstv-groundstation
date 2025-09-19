import os
import requests
from datetime import datetime, timedelta
from flask import render_template, current_app, redirect, url_for, flash, jsonify
from skyfield.api import Loader, Topos
from zoneinfo import ZoneInfo

from . import bp

TLE_SOURCE_URL = "https://celestrak.org/NORAD/elements/active.txt"

def tle_file_path():
    return os.path.join(current_app.config["TLE_DIR"], "active.txt")

def load_tle_satellites():
    """Load satellites from the TLE file."""
    tle_path = tle_file_path()
    if not os.path.exists(tle_path):
        return None, []
    with open(tle_path) as f:
        lines = [line.strip() for line in f if line.strip()]
    satellites = [lines[i] for i in range(0, len(lines), 3)]
    return tle_path, satellites

def get_tle_age_days(tle_path):
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
        epoch = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
        return round((datetime.utcnow() - epoch).total_seconds() / 86400, 1)
    except Exception:
        return None

@bp.route("/", endpoint="passes_page")
def passes_page():
    lat = current_app.config.get("LATITUDE")
    lon = current_app.config.get("LONGITUDE")
    alt = current_app.config.get("ALTITUDE_M")
    tz = current_app.config.get("TIMEZONE")

    tle_path, satellites = load_tle_satellites()
    tle_info = None
    passes = []

    if tle_path:
        mtime = datetime.fromtimestamp(os.path.getmtime(tle_path))
        tle_info = {
            "filename": os.path.basename(tle_path),
            "last_updated": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            "age_days": get_tle_age_days(tle_path)
        }

        if None not in (lat, lon, alt, tz):
            # Predict passes for next 24 hours
            load = Loader("./skyfield_data")
            ts = load.timescale()
            observer = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)

            with open(tle_path) as f:
                lines = [line.strip() for line in f if line.strip()]
            target_sats = ["ISS", "UMKA-1"]
            for i in range(0, len(lines), 3):
                try:
                    name = lines[i].strip()
                    if name.upper() not in [s.upper() for s in target_sats]:
                        continue
                    l1, l2 = lines[i+1], lines[i+2]
                    sat = load.tle(name, l1, l2)
                except Exception:
                    continue

                now = datetime.utcnow()
                end_time = now + timedelta(hours=24)
                t0 = ts.utc(now.year, now.month, now.day, now.hour, now.minute)
                t1 = ts.utc(end_time.year, end_time.month, end_time.day, end_time.hour, end_time.minute)

                try:
                    times, events = sat.find_events(observer, t0, t1, altitude_degrees=10.0)
                except Exception:
                    continue

                for ti, event in zip(times, events):
                    local_time = ti.utc_datetime().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(tz))
                    passes.append({
                        "satellite": name,
                        "time": local_time,
                        "event": ["rise", "culminate", "set"][event]
                    })

            passes.sort(key=lambda p: p["time"])

    return render_template("passes/passes.html",
                           tle_info=tle_info,
                           satellites=satellites,
                           passes=passes,
                           timezone=tz,
                           now=datetime.now(ZoneInfo(tz)),
                           location_set=None not in (lat, lon, alt, tz))

@bp.route("/update-tle", endpoint="update_tle")
def update_tle():
    try:
        resp = requests.get(TLE_SOURCE_URL, timeout=10)
        resp.raise_for_status()

        tle_dir = current_app.config["TLE_DIR"]
        os.makedirs(tle_dir, exist_ok=True)

        path = os.path.join(tle_dir, "active.txt")
        print("Saving TLE to:", path)
        print("TLE_DIR exists:", os.path.exists(tle_dir))

        with open(path, "w") as f:
            f.write(resp.text)

        print("TLE saved successfully.")
        return jsonify({"status": "success", "updated": True})
    except Exception as e:
        print("TLE update failed:", e)
        return jsonify({"status": "error", "message": str(e)})
        
