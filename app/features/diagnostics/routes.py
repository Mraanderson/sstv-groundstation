import subprocess
from flask import render_template, jsonify
from app.features.diagnostics import bp

@bp.route("/")
def diagnostics_page():
    return render_template("diagnostics/diagnostics.html")

@bp.route("/check")
def diagnostics_check():
    """Run rtl_test -t briefly and return output."""
    try:
        # Run rtl_test with a short timeout
        result = subprocess.run(
            ["rtl_test", "-t"],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout + result.stderr
        success = "Reading samples" in output or "Found Rafael" in output
        return jsonify({"success": success, "output": output})
    except Exception as e:
        return jsonify({"success": False, "output": str(e)})
        
