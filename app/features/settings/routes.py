from flask import render_template
from . import bp

@bp.route("/settings/import", endpoint='import_settings')
def import_settings():
    # Placeholder for import settings logic
    return render_template("settings/import_settings.html")

@bp.route("/settings/export", endpoint='export_settings')
def export_settings():
    # Placeholder for export settings logic
    return render_template("settings/export_settings.html")
  
