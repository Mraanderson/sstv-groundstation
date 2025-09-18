import os
import json
from flask import (
    request, current_app, jsonify, send_file,
    redirect, url_for, flash, render_template
)
from werkzeug.utils import secure_filename
from . import bp

# Path to the user config file (project root)
CONFIG_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "user_config.json")
)

@bp.route("/set-theme", methods=["POST"], endpoint="set_theme")
def set_theme():
    """Update theme in config and save."""
    data = request.get_json()
    theme = data.get("theme", "auto")
    current_app.config["THEME"] = theme
    if hasattr(current_app, "save_user_config"):
        current_app.save_user_config()
    return jsonify(success=True)

@bp.route("/import", methods=["GET", "POST"], endpoint="import_settings")
def import_settings():
    """Import settings from uploaded JSON file."""
    if request.method == "POST":
        file = request.files.get("settings_file")
        if file:
            filename = secure_filename(file.filename)
            if filename.lower().endswith(".json"):
                os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
                file.save(CONFIG_FILE)
                try:
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
                except Exception as e:
                    flash(f"Failed to read imported settings: {e}", "danger")
                return redirect(url_for("config.config_page"))
            else:
                flash("Invalid file type. Please upload a JSON file.", "danger")
    return render_template("settings/import_settings.html")

@bp.route("/export", methods=["GET"], endpoint="export_settings")
def export_settings():
    """Export current settings as JSON file."""
    if os.path.exists(CONFIG_FILE):
        return send_file(CONFIG_FILE, as_attachment=True, download_name="user_config.json")
    flash("No settings file found to export. Please save your configuration first.", "warning")
    return redirect(url_for("config.config_page"))
    
