from flask import Flask, render_template, send_from_directory, request, redirect, url_for
import os
import json
import time
import subprocess
import re
import requests
from datetime import datetime, timedelta, timezone
from skyfield.api import Loader, wgs84

app = Flask(__name__)

# --- Paths ---
IMAGES_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'images'))
TLE_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'tle'))
CONFIG_FILE = os.path.join(app.root_path, 'config.json')
SATELLITES_FILE = os.path.join(app.root_path, 'satellites.json')

# --- Gallery helpers ---
def get_all_images():
    image_files = []
    for root, dirs, files in os.walk(IMAGES_DIR):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                rel_dir = os.path.relpath(root, IMAGES_DIR)
                rel_path = os.path.join(rel_dir, file) if rel_dir != '.' else file
                image_files.append(rel_path.replace("\\", "/"))
    return sorted(image_files)

# --- Routes: Gallery ---
@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)

@app.route("/")
@app.route("/gallery")
def gallery():
    return render_template("gallery.html", image_names=get_all_images())

# --- Routes: Config ---
@app.route("/config", methods=["GET", "POST"])
def config_page():
    allowed_keys = ["location_lat", "location_lon", "location_alt", "timezone"]
    message = None

    if request.method == "POST":
        new_config = {key: request.form.get(key, "") for key in allowed_keys}
        with open(CONFIG_FILE, "w") as f:
            json.dump(new_config, f, indent=4)
        message = "Configuration updated successfully."

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config_data = json.load(f)
    else:
        config_data = {key: "" for key in allowed_keys}

    return render_template("config.html", config_data=config_data, message=message)

# --- TLE viewer helpers ---
def get_tle_files():
    tle_files = []
    if os.path.exists(TLE_DIR):
        for filename in sorted(os.listdir(TLE_DIR)):
            if filename.lower().endswith(".txt"):
                file_path = os.path.join(TLE_DIR, filename)
                with open(file_path) as f:
                    contents = f.read().strip()
                last_updated = time.strftime('%Y-%m-%d %H:%M:%S',
                                              time.localtime(os.path.getmtime(file_path)))
                tle_files.append({
                    "name": filename,
                    "last_updated": last_updated,
                    "contents": contents
                })
    return tle_files

def tle_view_with_message(message=None):
    return render_template("tle_view.html", tle_files=get_tle_files(), message=message)

# --- Routes: TLE viewer ---
@app.route("/tle")
def tle_view():
    return tle_view_with_message()

# --- Routes: Update All TLEs ---
@app.route("/tle/update-all", methods=["POST"])
def update_all_tles():
    try:
        script_path = os.path.abspath(os.path.join(app.root_path, "update_all_tles.py"))
        subprocess.run(["python3", script_path], check=True)
        message = "All TLEs updated successfully."
    except subprocess.CalledProcessError as e:
        message = f"Error updating TLEs: {e}"
    return tle_view_with_message(message)

# --- Routes: Install Cron Job ---
@app.route("/tle/install-cron", methods=["POST"])
def install_tle_cron():
    try:
        script_path = os.path.abspath(os.path.join(app.root_path, "update_all_tles.py"))
        cron_line = f"0 6 * * * /usr/bin/python3 {script_path} >> /tmp/tle_update.log 2>&1"
        subprocess.run(f'(crontab -l; echo "{cron_line}") | crontab -', shell=True, check=True)
        message = "Cron job installed to update TLEs daily at 06:00."
    except subprocess.CalledProcessError as e:
        message = f"Error installing cron job: {e}"
    return tle_view_with_message(message)
    # --- Refresh satellite list from CelesTrak ---
@app.route("/tle/refresh-list", methods=["POST"])
def refresh_satellite_list():
    existing = {}
    if os.path.exists(SATELLITES_FILE):
        with open(SATELLITES_FILE) as f:
            existing = json.load(f)

    satellites = {}
    for source_name, url in SOURCES.items():
        names = fetch_satellite_names(url)
        for name in names:
            satellites[name] = {
                "display_name": name,
                # Preserve enabled state if it exists, else use AUTO_ENABLE default
                "enabled": existing.get(name, {}).get("enabled", name in AUTO_ENABLE),
                "tle_url": url,
                "filename": safe_filename(name)
            }
    with open(SATELLITES_FILE, "w") as f:
        json.dump(satellites, f, indent=4)
    return redirect(url_for('tle_manage'))

# --- Manage satellites ---
@app.route("/tle/manage", methods=["GET", "POST"])
def tle_manage():
    message = None
    if request.method == "POST":
        if os.path.exists(SATELLITES_FILE):
            with open(SATELLITES_FILE) as f:
                satellites = json.load(f)
            for sat in satellites:
                satellites[sat]["enabled"] = sat in request.form
            with open(SATELLITES_FILE, "w") as f:
                json.dump(satellites, f, indent=4)
            message = "Satellite selection updated."
    if os.path.exists(SATELLITES_FILE):
        with open(SATELLITES_FILE) as f:
            satellites = json.load(f)
    else:
        satellites = {}
    sstv_sats = {k: v for k, v in satellites.items() if k in AUTO_ENABLE}
    other_sats = {k: v for k, v in satellites.items() if k not in AUTO_ENABLE}
    return render_template("tle_manage.html", sstv_sats=sstv_sats, other_sats=other_sats, message=message)

# --- Import settings ---
@app.route("/import-settings", methods=["GET", "POST"])
def import_settings():
    message = None
    if request.method == "POST":
        file = request.files.get("settings_file")
        if file and file.filename.endswith(".json"):
            try:
                data = json.load(file)
                with open(CONFIG_FILE, "w") as f:
                    json.dump(data.get("config", {}), f, indent=4)
                with open(SATELLITES_FILE, "w") as f:
                    json.dump(data.get("satellites", {}), f, indent=4)
                message = "Settings imported successfully."
            except Exception as e:
                message = f"Error importing settings: {e}"
        else:
            message = "Please upload a valid .json file."
    return render_template("import_settings.html", message=message)

# --- Export settings ---
@app.route("/export-settings")
def export_settings():
    data = {"config": {}, "satellites": {}}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            data["config"] = json.load(f)
    if os.path.exists(SATELLITES_FILE):
        with open(SATELLITES_FILE) as f:
            data["satellites"] = json.load(f)
    return app.response_class(
        json.dumps(data, indent=4),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=settings.json"}
    )

@app.route("/export-settings-page")
def export_settings_page():
    return render_template("export_settings.html")

# --- Pass prediction route ---
@app.route("/passes")
def passes_page():
    if not os.path.exists(CONFIG_FILE):
        return render_template("passes.html", passes=[], message="No station config found.")
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    try:
        lat = float(cfg.get("location_lat", 0))
        lon = float(cfg.get("location_lon", 0))
        alt = float(cfg.get("location_alt", 0))
    except ValueError:
        return render_template("passes.html", passes=[], message="Invalid station coordinates.")

    if not os.path.exists(SATELLITES_FILE):
        return render_template("passes.html", passes=[], message="No satellites.json found.")
    with open(SATELLITES_FILE) as f:
        sats = json.load(f)
    enabled = [name for name, data in sats.items() if data.get("enabled")]

    if not enabled:
        return render_template("passes.html", passes=[], message="No satellites enabled.")

    # Skyfield setup
    load = Loader('./skyfield_data')
    ts = load.timescale()
    observer = wgs84.latlon(lat, lon, alt)

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(hours=24)

    passes = []

    for sat_name in enabled:
        tle_file = os.path.join(TLE_DIR, sats[sat_name]["filename"])
        if not os.path.exists(tle_file):
            continue
        with open(tle_file) as f:
            lines = f.read().strip().splitlines()
            if len(lines) < 3:
                continue
            name, l1, l2 = lines[0], lines[1], lines[2]
        sat = load.tle(name, l1, l2)

        # Find passes
        t0 = ts.from_datetime(now)
        t1 = ts.from_datetime(end_time)
        try:
            t, events = sat.find_events(observer, t0, t1, altitude_degrees=10.0)
        except Exception:
            continue

        current_pass = {}
        for ti, event in zip(t, events):
            if event == 0:  # rise
                current_pass = {"satellite": sat_name, "aos": ti.utc_datetime()}
            elif event == 1:  # culminate
                current_pass["max_elev"] = sat.at(ti).altaz()[0].degrees
            elif event == 2:  # set
                current_pass["los"] = ti.utc_datetime()
                if "aos" in current_pass and "los" in current_pass:
                    current_pass["duration"] = (current_pass["los"] - current_pass["aos"]).seconds
                    passes.append(current_pass)
                current_pass = {}

    passes.sort(key=lambda p: p["aos"])
    return render_template("passes.html", passes=passes, message=None)

# --- Run the app ---
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
    
