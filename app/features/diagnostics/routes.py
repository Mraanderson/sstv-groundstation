import os
import json
import shutil
import subprocess
from flask import render_template, jsonify
from app.features.diagnostics import bp

# File where the scheduler writes current pass info
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
    Adds IQ file size if the file exists.
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

            # Add file size if IQ file exists
            iq_path = pass_info.get("iq_file")
            if iq_path and os.path.exists(iq_path):
                size_mb = os.path.getsize(iq_path) / (1024*1024)
                pass_info["iq_size_mb"] = round(size_mb, 2)

        except Exception as e:
            pass_info = {"error": f"Could not read pass state: {e}"}

    return jsonify({
        "disk_free_gb": free_gb,
        "pass_info": pass_info
    })
    
