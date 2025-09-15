from flask import Flask, render_template, send_from_directory, request
import os, json, time

app = Flask(__name__)

# Point to the root-level images folder (one level up from app/)
IMAGES_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'images'))
CONFIG_FILE = os.path.join(app.root_path, 'config.json')

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

@app.route("/tle/manage")
def tle_manage():
    return "<h1>TLE management page coming soon</h1>"

@app.route("/config", methods=["GET", "POST"])
def config_page():
    message = None
    if request.method == "POST":
        new_config = {key: request.form[key] for key in request.form}
        with open(CONFIG_FILE, "w") as f:
            json.dump(new_config, f, indent=4)
        message = "Configuration updated successfully."
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config_data = json.load(f)
    else:
        config_data = {}
    return render_template("config.html", config_data=config_data, message=message)

if __name__ == "__main__":
    print("Looking for images in:", IMAGES_DIR)  # Debugging helper
    app.run(host="0.0.0.0", port=5000, debug=True)
    
