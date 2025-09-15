import os
import json
from flask import Flask, render_template, request, send_from_directory, jsonify
import requests

app = Flask(__name__)

# Paths
ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.abspath(os.path.join(ROOT, "..", "images"))
CONFIG_PATH = os.path.join(ROOT, "config.json")

# Ensure images folder exists
os.makedirs(IMG_DIR, exist_ok=True)

# ----------------------
# Config load/save
# ----------------------
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass  # fall back to defaults if file is corrupted
    return {
        "latitude": "",
        "longitude": "",
        "elevation": "",
        "satellite": "",
        "tle_group": "",
        "frequency": "",
        "sstv_mode": ""
    }

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

# ----------------------
# Routes
# ----------------------
@app.route("/config", methods=["GET", "POST"])
def config():
    config = load_config()
    if request.method == "POST":
        for key in config.keys():
            if key in request.form:
                config[key] = request.form[key]
        save_config(config)

    # Get the 8 most recent images
    images = sorted(os.listdir(IMG_DIR), reverse=True)
    recent_images = [
        img for img in images
        if img.lower().endswith((".png", ".jpg", ".jpeg"))
    ][:8]

    return render_template("config.html", config=config, recent_images=recent_images)

@app.route("/gallery")
def gallery():
    images = sorted(os.listdir(IMG_DIR), reverse=True)
    all_images = [
        img for img in images
        if img.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    return render_template("gallery.html", all_images=all_images)

@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMG_DIR, filename)

@app.route("/get-satellites")
def get_satellites():
    tle_group = request.args.get("tle_group", "amateur")
    url = f"https://celestrak.org/NORAD/elements/{tle_group}.txt"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        lines = response.text.strip().split("\n")
        satellites = [lines[i].strip() for i in range(0, len(lines), 3)]
        return jsonify(satellites)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------
# Main entry
# ----------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
    
