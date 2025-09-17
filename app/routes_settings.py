import os, json
from flask import Blueprint, render_template, request, Response
from .utils import CONFIG_FILE

bp = Blueprint('settings', __name__)

@bp.route("/import-settings", methods=["GET", "POST"])
def import_settings():
    msg = None
    if request.method == "POST":
        file = request.files.get("settings_file")
        if file and file.filename.endswith(".json"):
            try:
                data = json.load(file)
                with open(CONFIG_FILE, "w") as f:
                    json.dump(data.get("config", {}), f, indent=4)
                msg = "Settings imported successfully."
            except Exception as e:
                msg = f"Error importing settings: {e}"
        else:
            msg = "Please upload a valid .json file."
    return render_template("import_settings.html", message=msg)

@bp.route("/export-settings")
def export_settings():
    data = {"config": {}}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            data["config"] = json.load(f)
    return Response(
        json.dumps(data, indent=4),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=settings.json"}
    )

@bp.route("/export-settings-page")
def export_settings_page():
    return render_template("export_settings.html")
    
