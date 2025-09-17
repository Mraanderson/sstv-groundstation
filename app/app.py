from flask import Flask, render_template, send_from_directory, request, redirect, url_for
import os
import json
from datetime import datetime, timedelta, timezone
import requests
from skyfield.api import Loader, wgs84, EarthSatellite

app = Flask(__name__)

# --- Paths ---
IMAGES_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'images'))
TLE_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'tle'))
CONFIG_FILE = os.path.join(app.root_path, 'config.json')
TLE_FILE = os.path.join(TLE_DIR, "iss__zarya_.txt")

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

# --- Config helpers ---
def config_exists_and_valid():
    if not os.path.exists(CONFIG_FILE):
        return False
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        for key in ["location_lat", "location_lon", "location_alt", "timezone"]:
            if not cfg.get(key):
                return False
        return True
    except Exception:
        return False

# --- TLE helpers ---
def get_tle_last_updated():
    if os.path.exists(TLE_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(TLE_FILE), tz=timezone.utc)
        return mtime.strftime("%Y-%m-%d %H:%M:%S UTC")
    return "Never"

def fetch_latest_tle():
    os.makedirs(TLE_DIR, exist_ok=True)
    tle_url = "https://celestrak.org/NORAD/elements/stations.txt"
    r = requests.get(tle_url, timeout=10)
    r.raise_for_status()
    lines = r.text.strip().splitlines()
    for i in range(len(lines)):
        if lines[i].upper().startswith("ISS"):
            with open(TLE_FILE, "w") as f:
                f.write("\n".join(lines[i:i+3]) + "\n")
            return True
    return False

def tle_needs_refresh(max_age_days=3):
    if not os.path.exists(TLE_FILE):
        return True
    mtime = datetime.fromtimestamp(os.path.getmtime(TLE_FILE), tz=timezone.utc)
    age_days = (datetime.now(timezone.utc) - mtime).total_seconds() / 86400.0
    return age_days > max_age_days

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

# --- Update TLE route ---
@app.route("/update-tle", methods=["POST"])
def update_tle():
    try:
        if fetch_latest_tle():
            message = "TLE updated successfully."
        else:
            message = "ISS TLE not found in source."
    except Exception as e:
        message = f"Error updating TLE: {e}"
    return redirect(url_for('passes_page'))

# --- Pass prediction for ISS ---
@app.route("/passes")
def passes_page():
    if not config_exists_and_valid():
        return redirect(url_for('config_page'))

    if tle_needs_refresh():
        try:
            fetch_latest_tle()
        except Exception as e:
            return render_template("passes.html", passes=[], message=f"TLE refresh failed: {e}", tle_last_updated=get_tle_last_updated())

    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    lat = float(cfg.get("location_lat", 0))
    lon = float(cfg.get("location_lon", 0))
    alt = float(cfg.get("location_alt", 0))

    with open(TLE_FILE) as f:
        lines = f.read().strip().splitlines()
        name, l1, l2 = lines[0], lines[1], lines[2]

    load = Loader('./skyfield_data')
    ts = load.timescale()
    observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)
    sat = EarthSatellite(l1, l2, name, ts)

    tle_epoch_dt = sat.epoch.utc_datetime().replace(tzinfo=timezone.utc)
    tle_age_days = (datetime.now(timezone.utc) - tle_epoch_dt).total_seconds() / 86400.0
    info = {
        "tle_epoch_utc": tle_epoch_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "tle_age_days": round(tle_age_days, 2),
        "observer": {"lat": lat, "lon": lon, "alt_m": alt},
        "min_elev_deg": 0.0
    }
    warning = "TLE is older than 7 days — refresh from CelesTrak." if tle_age_days > 7 else None

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(hours=24)

    passes = []
    try:
        t, events = sat.find_events(
            observer,
            ts.from_datetime(now),
            ts.from_datetime(end_time),
            altitude_degrees=info["min_elev_deg"]
        )
    except Exception as e:
        return render_template("passes.html", passes=[], message=f"Error finding passes: {e}", info=info, tle_last_updated=get_tle_last_updated())

    current_pass = {}
    for ti, event in zip(t, events):
        if event == 0:
            current_pass = {"satellite": "ISS (ZARYA)", "aos": ti.utc_datetime()}
        elif event == 1:
            topocentric = (sat - observer).at(ti)
            alt_deg, az, distance = topocentric.altaz()
            current_pass["max_elev"] = alt_deg.degrees
        elif event == 2:
            current_pass["los"] = ti.utc_datetime()
            if "aos" in current_pass and "los" in current_pass:
                current_pass["duration"] = (current_pass["los"] - current_pass["aos"]).seconds
                passes.append(current_pass)
            current_pass = {}

    passes.sort(key=lambda p: p["aos"])
    return render_template("passes.html", passes=passes, message=warning, info=info, tle_last_updated=get_tle_last_updated())

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
                message = "Settings imported successfully."
            except Exception as e:
                message = f"Error importing settings: {e}"
        else:
            message = "Please upload a valid .json file."
    return render_template("import_settings.html", message=message)

# --- Export settings ---
@app.route("/export-settings")
def export_settings():
    data = {"config": {}}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            data["config"] = json.load(f)
    return app.response_class(
        json.dumps(data, indent=4),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=settings.json"}
    )

@app.route("/export-settings-page")
def export_settings_page():
    return render_template("export_settings.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
    
