import os
import requests
from datetime import datetime
from flask import render_template, current_app, redirect, url_for, flash
from . import bp

TLE_SOURCE_URL = "https://celestrak.org/NORAD/elements/active.txt"

def tle_file_path():
    return os.path.join(current_app.config["TLE_DIR"], "active.txt")

@bp.route("/", endpoint="passes_page")
def passes_page():
    tle_path = tle_file_path()
    tle_info = None
    satellites = []

    if os.path.exists(tle_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(tle_path))
        tle_info = {
            "filename": os.path.basename(tle_path),
            "last_updated": mtime.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(tle_path) as f:
            lines = [line.strip() for line in f if line.strip()]
            satellites = [lines[i] for i in range(0, len(lines), 3)]

    return render_template("passes/passes.html",
                           tle_info=tle_info,
                           satellites=satellites)

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
    
