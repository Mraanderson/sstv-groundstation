import os
import json
from flask import request, current_app, jsonify, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
from . import bp

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "user_config.json")

@bp.route("/set-theme", methods=["POST"], endpoint="set_theme")
def set_theme():
    data = request.get_json()
    theme = data.get("theme", "auto")
    current_app.config["THEME"] = theme
    current_app.save_user_config()
    return jsonify(success=True)

@bp.route("/import", methods=["GET", "POST"], endpoint="import_settings")
def import_settings():
    if request.method == "POST":
        file = request.files.get("settings_file")
        if file:
            filename = secure_filename(file.filename)
            if filename.lower().endswith(".json"):
                file.save(CONFIG_FILE)
                # Reload into app.config
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                current_app.config.update(
                    LATITUDE=data.get("latitude"),
                    LONGITUDE=data.get("longitude"),
                    ALTITUDE_M=data.get("altitude_m"),
                    TIMEZONE=data.get("timezone"),
                    THEME=data.get("theme", "auto")
                )
                flash("Settings imported successfully.", "success")
                return redirect(url_for("config.config_page"))
    return current_app.send_static_file("settings/import_settings.html")

@bp.route("/export", methods=["GET"], endpoint="export_settings")
def export_settings():
    return send_file(CONFIG_FILE, as_attachment=True, download_name="user_config.json")
    
