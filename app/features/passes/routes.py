import os
import requests
from datetime import datetime, timedelta
from flask import render_template, current_app, redirect, url_for, flash
from skyfield.api import Loader, Topos

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
        }

        if None not in (lat, lon, alt, tz):
            # Predict passes for next 24 hours
            load = Loader("./skyfield_data")
            ts = load.timescale()
            observer = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)

            with open(tle_path) as f:
                lines = [line.strip() for line in f if line.strip()]
            for i in range(0, len(lines), 3):
                try:
                    name, l1, l2 = lines[i], lines[i+1], lines[i+2]
                except IndexError:
                    continue
                sat = load.tle(name, l1, l2)
                now = datetime.utcnow()
                end_time = now + timedelta(hours=24)
                t0 = ts.utc(now.year, now.month, now.day, now.hour, now.minute)
                t1 = ts.utc(end_time.year, end_time.month, end_time.day, end_time.hour, end_time.minute)
                try:
                    times, events = sat.find_events(observer, t0, t1, altitude_degrees=10.0)
                except Exception:
                    continue
                for ti, event in zip(times, events):
                    passes.append({
                        "satellite": name,
                        "time": ti.utc_datetime().astimezone(),
                        "event": ["rise", "culminate", "set"][event]
                    })

            passes.sort(key=lambda p: p["time"])

    return render_template("passes/passes.html",
                           tle_info=tle_info,
                           satellites=satellites,
                           passes=passes,
                           location_set=None not in (lat, lon, alt, tz))

@bp.route("/update-tle", endpoint="update_tle")
def update_tle():
    try:
        resp = requests.get(TLE_SOURCE_URL, timeout=10)
        resp.raise_for_status()
        os.makedirs(current_app.config["TLE_DIR"], exist_ok=True)
        with open(tle_file_path(), "w") as f:
            f.write(resp.text)
        flash("TLE data updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update TLE data: {e}", "danger")
    return redirect(url_for("passes.passes_page"))
    
