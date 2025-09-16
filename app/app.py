from flask import Flask, render_template, send_from_directory, request
import os
import json
import re
from datetime import datetime, timedelta, timezone
from skyfield.api import Loader, wgs84

app = Flask(__name__)

# --- Paths ---
IMAGES_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'images'))
TLE_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'tle'))
CONFIG_FILE = os.path.join(app.root_path, 'config.json')

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

# --- Routes: Pass prediction for ISS ---
@app.route("/passes")
def passes_page():
    sat_name = "ISS (ZARYA)"
    safe_name = re.sub(r"[^A-Za-z0-9_\-]", "_", sat_name.lower())
    tle_path = os.path.join(TLE_DIR, f"{safe_name}.txt")

    if not os.path.exists(tle_path):
        return render_template("passes.html", passes=[], message="ISS TLE file not found.")

    if not os.path.exists(CONFIG_FILE):
        return render_template("passes.html", passes=[], message="Station location not configured.")

    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    try:
        lat = float(cfg.get("location_lat", 0))
        lon = float(cfg.get("location_lon", 0))
        alt = float(cfg.get("location_alt", 0))
    except ValueError:
        return render_template("passes.html", passes=[], message="Invalid station coordinates.")

    with open(tle_path) as f:
        lines = f.read().strip().splitlines()
        if len(lines) < 3:
            return render_template("passes.html", passes=[], message="ISS TLE file incomplete.")
        name, l1, l2 = lines[0], lines[1], lines[2]

    load = Loader('./skyfield_data')
    ts = load.timescale()
    observer = wgs84.latlon(lat, lon, alt)
    sat = load.tle(name, l1, l2)

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(hours=24)

    passes = []
    try:
        t, events = sat.find_events(observer, ts.from_datetime(now), ts.from_datetime(end_time), altitude_degrees=10.0)
    except Exception as e:
        return render_template("passes.html", passes=[], message=f"Error finding passes: {e}")

    current_pass = {}
    for ti, event in zip(t, events):
        if event == 0:
            current_pass = {"satellite": sat_name, "aos": ti.utc_datetime()}
        elif event == 1:
            current_pass["max_elev"] = sat.at(ti).altaz()[0].degrees
        elif event == 2:
            current_pass["los"] = ti.utc_datetime()
            if "aos" in current_pass and "los" in current_pass:
                current_pass["duration"] = (current_pass["los"] - current_pass["aos"]).seconds
                passes.append(current_pass)
            current_pass = {}

    passes.sort(key=lambda p: p["aos"])
    return render_template("passes.html", passes=passes, message=None)

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
    
