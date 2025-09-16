SSTV Groundstation – AI Context Summary

Overview:
SSTV Groundstation is a Flask-based web application for managing a satellite ground station focused on Slow Scan Television (SSTV) reception. It provides a mobile‑friendly, app‑like interface for:
- Viewing and managing received SSTV images
- Configuring station location and timezone
- Managing and updating satellite TLEs
- Importing and exporting station settings

Key Features:

Image Gallery:
- Displays all received images from the images/ directory.
- Responsive grid layout using Bootstrap for mobile and desktop.
- Click/tap to view full‑size images in a new tab.

Station Configuration:
- Editable Latitude, Longitude, Altitude, and Timezone.
- Interactive Leaflet.js map for selecting location.
- Auto‑fill from browser geolocation.
- Auto‑fetch altitude from Open‑Elevation API.
- Auto‑detect timezone from browser.
- Save button disabled until all fields are valid.

Satellite Management:
- Known SSTV Satellites auto‑enabled and displayed in a highlighted section.
- Refresh satellite list from CelesTrak (stations + amateur lists).
- Auto‑generate satellites.json with TLE source URLs and filenames.
- Enable/disable satellites via touch‑friendly checkboxes.
- Import/export satellite selection.

TLE Viewer:
- Lists all .txt TLE files from the tle/ directory.
- Shows last updated timestamp.
- Scrollable, monospaced TLE content blocks.
- Buttons to update all TLEs via update_all_tles.py and install a daily cron job for automatic updates.

Settings Import/Export:
- Import: Upload .json file containing config and satellite list.
- Export: Download current config and satellite list as .json.
- Both pages styled for mobile with clear instructions and full‑width buttons.

UI/UX Enhancements:
- Bootstrap 5 integration for responsive, mobile‑first design.
- Dark theme with neon green accents for a control‑panel feel.
- Fixed bottom navigation bar with quick links: Gallery, Satellites, Config, Import, Export.
- Consistent card‑based layout for all forms and lists.
- Touch‑friendly form controls and buttons.

File Structure (Key Files):
app/
├── app.py
├── templates/
│   ├── base.html
│   ├── gallery.html
│   ├── config.html
│   ├── tle_manage.html
│   ├── tle_view.html
│   ├── import_settings.html
│   ├── export_settings.html
images/
tle/
config.json
satellites.json

Known SSTV Auto‑Enable List:
ISS (ZARYA)
ARCTICSAT 1
UMKA 1
SONATE 2
FRAM2HAM

Requirements:
- Python 3.8+
- Flask
- Requests
- Bootstrap 5 (via CDN)
- Leaflet.js (via CDN)

Running the App:
cd app
python3 app.py
Then open http://localhost:5000 in your browser.

Recent Changes:
- Added mobile‑friendly Bootstrap UI across all pages.
- Added fixed bottom nav for quick navigation.
- Integrated Leaflet map and Open‑Elevation API into config page.
- Auto‑detect timezone in config page.
- Save button validation for config form.
- Grouped SSTV satellites at top of /tle/manage.
- Added dedicated Import and Export pages with consistent styling.

templates/base.html:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}SSTV Groundstation{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #111; color: #eee; font-family: system-ui, sans-serif; margin-bottom: 60px; }
        .app-header { background-color: #222; padding: 0.75rem 1rem; font-size: 1.25rem; font-weight: bold; color: #0f0; text-align: center; border-bottom: 2px solid #0f0; }
        .card { background-color: #1a1a1a; border: 1px solid #333; border-radius: 0.75rem; }
        .btn-primary { background-color: #0f0; border-color: #0f0; color: #000; }
        .btn-primary:hover { background-color: #0c0; border-color: #0c0; }
        .navbar-dark .nav-link { color: #0f0; }
        .navbar-dark .nav-link.active { font-weight: bold; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="app-header">SSTV Groundstation</div>
    <div class="container py-3">
        {% block content %}{% endblock %}
    </div>
    <nav class="navbar fixed-bottom navbar-dark bg-dark border-top border-success">
        <div class="container-fluid justify-content-around">
            <a class="nav-link {% if request.endpoint == 'gallery' %}active{% endif %}" href="{{ url_for('gallery') }}">Gallery</a>
            <a class="nav-link {% if request.endpoint == 'tle_manage' %}active{% endif %}" href="{{ url_for('tle_manage') }}">Satellites</a>
            <a class="nav-link {% if request.endpoint == 'config_page' %}active{% endif %}" href="{{ url_for('config_page') }}">Config</a>
            <a class="nav-link {% if request.endpoint == 'import_settings' %}active{% endif %}" href="{{ url_for('import_settings') }}">Import</a>
            <a class="nav-link {% if request.endpoint == 'export_settings_page' %}active{% endif %}" href="{{ url_for('export_settings_page') }}">Export</a>
        </div>
    </nav>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>

app/app.py:
from flask import Flask, render_template, send_from_directory, request, redirect, url_for
import os, json, time, subprocess, re, requests

app = Flask(__name__)

IMAGES_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'images'))
TLE_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'tle'))
CONFIG_FILE = os.path.join(app.root_path, 'config.json')
SATELLITES_FILE = os.path.join(app.root_path, 'satellites.json')

def get_all_images():
    image_files = []
    for root, dirs, files in os.walk(IMAGES_DIR):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                rel_dir = os.path.relpath(root, IMAGES_DIR)
                rel_path = os.path.join(rel_dir, file) if rel_dir != '.' else file
                image_files.append(rel_path.replace("\\", "/"))
    return sorted(image_files)

@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)

@app.route("/")
@app.route("/gallery")
def gallery():
    return render_template("gallery.html", image_names=get_all_images())

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

@app.route("/tle")
def tle_view():
    return tle_view_with_message()

@app.route("/tle/update-all
