from flask import Flask, render_template, send_from_directory, request
import os
import json
import time
import subprocess
import re
import requests

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

# --- Routes: Config (lat/lon/alt/timezone only) ---
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

# --- Helper: Generate satellites.json from CelesTrak ---
SOURCES = {
    "stations": "https://celestrak.org/NORAD/elements/stations.txt",
    "amateur": "https://celestrak.org/NORAD/elements/amateur.txt"
}

AUTO_ENABLE = {"ISS (ZARYA)", "ARCTICSAT 1", "UMKA 1", "SONATE 2", "FRAM2HAM"}

def fetch_satellite_names(url):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    lines = r.text.strip().splitlines()
    return [lines[i].strip() for i in range(0, len(lines), 3)]

def safe_filename(name):
    return re.sub(r'[^A-Za-z0-9_\-]', '_', name.lower()) + ".txt"

@app.route("/tle/refresh-list", methods=["POST"])
def refresh_satellite_list():
    satellites = {}
    for source_name, url in SOURCES.items():
        names = fetch_satellite_names(url)
        for name in names:
            satellites[name] = {
                "display_name": name,
                "enabled": name in AUTO_ENABLE,
                "tle_url": url,
                "filename": safe_filename(name)
            }
    with open(SATELLITES_FILE, "w") as f:
        json.dump(satellites, f, indent=4)
    return redirect(url_for('tle_manage'))

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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")

