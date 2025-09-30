import os
import json
import shutil
import subprocess
from flask import render_template, jsonify
from app.features.diagnostics import bp

# File where the scheduler can write current pass info
STATE_FILE = os.path.expanduser("~/sstv-groundstation/current_pass.json")

@bp.route("/")
def diagnostics_page():
    return render_template("diagnostics/diagnostics.html")

@bp.route("/check")
def diagnostics_check():
    """Run rtl_test -t briefly and return output."""
    try:
        result = subprocess.run(
            ["rtl_test", "-t"],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout + result.stderr
        success = "Reading samples" in output or "Found Rafael" in output
        return jsonify({"success": success, "output": output})
    except Exception as e:
        return jsonify({"success": False, "output": str(e)})

@bp.route("/status")
def diagnostics_status():
    """
    Return current pass info (if any) and free disk space in GB.
    Expects the scheduler to write/remove STATE_FILE during passes.
    """
    # Disk usage
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (2**30)

    # Pass state
    pass_info = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                pass_info = json.load(f)
        except Exception:
            pass_info = {"error": "Could not read pass state"}

    return jsonify({
        "disk_free_gb": free_gb,
        "pass_info": pass_info
    })
