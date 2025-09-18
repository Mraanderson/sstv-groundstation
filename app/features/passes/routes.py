from flask import render_template
from . import bp

@bp.route("/passes", endpoint='passes_page')
def passes_page():
    # Placeholder data for now — will be replaced with real pass predictions
    passes = [
        {"satellite": "ISS (ZARYA)", "start": "2025-09-18 10:00", "end": "2025-09-18 10:12", "max_elevation": "45°"},
        {"satellite": "NOAA 19", "start": "2025-09-18 11:30", "end": "2025-09-18 11:42", "max_elevation": "30°"}
    ]
    return render_template("passes/passes.html", passes=passes)
  
