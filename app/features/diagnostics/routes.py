def check_system_requirements():
    """Check for required system binaries (not in venv)."""
    import shutil
    required = [
        {"name": "sox", "desc": "Audio conversion (sox)"},
        {"name": "rtl_sdr", "desc": "RTL-SDR IQ capture (rtl_sdr)"},
        #{"name": "sstv", "desc": "SSTV decoder (sstv)"},
        #{"name": "rxsstv", "desc": "SSTV decoder (rxsstv)"},
    ]
    results = []
    for r in required:
        path = shutil.which(r["name"])
        results.append({
            "name": r["name"],
            "desc": r["desc"],
            "found": bool(path),
            "path": path or "Not found"
        })
    return results
import os
import json
import shutil
import subprocess
from pathlib import Path
from flask import render_template, jsonify, request
from app.utils.iq_cleanup import cleanup_orphan_iq
from app.features.diagnostics import bp


@bp.route("/clear_all_iq", methods=["POST"])
def clear_all_iq():
    """Delete all orphan IQ files (not in use by a current pass)."""
    deleted = cleanup_orphan_iq()
    return jsonify({"success": True, "deleted": deleted, "count": len(deleted)})

# File where the scheduler writes current pass info
STATE_FILE = os.path.expanduser("~/sstv-groundstation/current_pass.json")
RECORDINGS_DIR = Path("recordings")
LOW_SPACE_GB = 2  # threshold for auto-cleanup

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
    Return current pass info (if any), free disk space in GB,
    and any orphan IQ files. Auto-delete orphans if disk < LOW_SPACE_GB.
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

    # Orphan IQ files
    orphan_iq = []
    for f in RECORDINGS_DIR.glob("*.iq"):
        if not pass_info or str(f) != pass_info.get("iq_file"):
            size_mb = f.stat().st_size / (1024*1024)
            entry = {"path": str(f), "size_mb": round(size_mb, 2)}
            # Auto-delete if dangerously low on space
            if free_gb < LOW_SPACE_GB:
                try:
                    os.remove(f)
                    entry["deleted"] = True
                except Exception as e:
                    entry["delete_error"] = str(e)
            orphan_iq.append(entry)

    return jsonify({
        "disk_free_gb": free_gb,
        "pass_info": pass_info,
        "orphan_iq": orphan_iq,
        "requirements": check_system_requirements()
    })

@bp.route("/delete_iq", methods=["POST"])
def delete_iq():
    """
    Manually delete a specified orphan IQ file.
    """
    try:
        data = request.get_json()
        path = data.get("path")
        if path and os.path.exists(path) and path.endswith(".iq"):
            os.remove(path)
            return jsonify({"success": True, "message": f"Deleted {path}"})
        return jsonify({"success": False, "message": "File not found"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
        
