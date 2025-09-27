from flask import render_template
from app.features.diagnostics import bp

@bp.route("/diagnostics")
def diagnostics_page():
    return render_template("diagnostics/diagnostics.html")
