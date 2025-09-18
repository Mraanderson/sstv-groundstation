import os
import requests
from flask import Blueprint, render_template, current_app, flash, redirect, url_for
from datetime import datetime, timedelta
from skyfield.api import Loader, EarthSatellite, Topos

bp = Blueprint("passes", __name__, template_folder="templates")

# Paths
TLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tle")
TLE_FILE = os.path.join(TLE_DIR, "stations.txt")
TLE_URL = "https://celestrak.org/NORAD/elements/stations.txt"

# Skyfield loader
sf_loader = Loader(os.path.join(os.path.dirname(__file__), "..", "..", "data", "skyfield"))
ts = sf_loader.timescale()

@bp.route("/update-tle", methods=["GET"], endpoint="update_tle")
def update_tle():
    """Fetch latest ISS TLE from Celestrak and save locally."""
    try:
        os.makedirs(TLE_DIR, exist_ok=True)
        resp = requests.get(TLE_URL, timeout=10)
        resp.raise_for_status()
        with open(TLE_FILE, "w", encoding="utf-8") as f:
            f.write(resp.text)
        flash("TLE updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update TLE: {e}", "danger")
    return redirect(url_for("passes.passes_page"))

@bp.route("/", methods=["GET"], endpoint="passes_page")
def passes_page():
    """Display upcoming ISS passes based on observer location."""
    # Load observer location from config
    lat = current_app.config.get("LATITUDE")
    lon = current_app.config.get("LONGITUDE")
    alt = current_app.config.get("ALTITUDE_M")
    tz = current_app.config.get("TIMEZONE")

    if not all([lat, lon, alt, tz]):
        flash("Observer location not set. Please configure your location first.", "warning")
        return render_template("passes/passes.html", passes=None, tle_info=None, error="Missing location data.")

    # Load TLE file
    if not os.path.exists(TLE_FILE):
        flash("TLE file not found. Please update TLE first.", "warning")
        return render_template("passes/passes.html", passes=None, tle_info=None, error="Missing TLE data.")

    try:
        with open(TLE_FILE, "r") as f:
            lines = f.readlines()

        satellites = []
        for i in range(0, len(lines), 3):
            name = lines[i].strip()
            line1 = lines[i + 1].strip()
            line2 = lines[i + 2].strip()
            satellites.append(EarthSatellite(line1, line2, name, ts))

        observer = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)
        now = ts.now()
        end = ts.utc(datetime.utcnow() + timedelta(hours=24))

        passes = []
        for sat in satellites:
            t0, events = sat.find_events(observer, now, end, altitude_degrees=10.0)
            for ti, event in zip(t0, events):
                label = {0: "AOS", 1: "MAX", 2: "LOS"}[event]
                passes.append({
                    "satellite": sat.name,
                    "event": label,
                    "time": ti.utc_datetime().astimezone()
                })

        passes.sort(key=lambda p: p["time"])

        tle_info = {
            "filename": os.path.basename(TLE_FILE),
            "last_updated": datetime.fromtimestamp(os.path.getmtime(TLE_FILE)).strftime("%Y-%m-%d %H:%M:%S")
        }

        return render_template("passes/passes.html", passes=passes, tle_info=tle_info, error=None)

    except Exception as e:
        flash(f"Error processing TLE data: {e}", "danger")
        return render_template("passes/passes.html", passes=None, tle_info=None, error="Failed to compute passes.")
        
