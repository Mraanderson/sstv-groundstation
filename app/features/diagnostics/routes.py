import os, json, shutil, subprocess, psutil, datetime
from pathlib import Path
from flask import render_template, jsonify, request, current_app, redirect, url_for, flash
from app.utils.iq_cleanup import cleanup_orphan_iq
from app.features.diagnostics import bp
from app.utils import passes as passes_utils
from app.utils.decoder import process_uploaded_wav

# --- Paths & constants ---
RECORDINGS_DIR = Path("recordings")
SETTINGS_FILE  = Path("settings.json")
IMAGES_DIR     = Path("images")
LOW_SPACE_GB   = 2
MANUAL_DIR     = RECORDINGS_DIR / "manual"
MANUAL_DIR.mkdir(parents=True, exist_ok=True)

# --- Settings helpers ---
def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}
    except Exception:
        return {}

def save_settings(s):
    SETTINGS_FILE.write_text(json.dumps(s, indent=2))

def get_ppm():
    try:
        return int(load_settings().get("rtl_ppm", 0))
    except (ValueError, TypeError):
        return 0

def get_gain():
    try:
        return str(load_settings().get("rtl_gain", "0"))
    except Exception:
        return "0"

def set_gain(g):
    s = load_settings()
    s["rtl_gain"] = str(g)
    save_settings(s)

def reset_ppm():
    s = load_settings()
    s["rtl_ppm"] = 0
    save_settings(s)

# --- SDR detection ---
def sdr_present():
    return bool(shutil.which("rtl_sdr"))

def sdr_device_connected():
    try:
        res = subprocess.run(["rtl_test", "-t"], capture_output=True, text=True, timeout=3)
        out = (res.stdout or "") + (res.stderr or "")
        return any(k in out for k in ("Reading samples", "Found Rafael"))
    except Exception:
        return False

def sdr_in_use():
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            if (proc.info["name"] and "rtl_fm" in proc.info["name"]) or (
                proc.info["cmdline"] and any("rtl_fm" in c for c in proc.info["cmdline"])
            ):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False
    # --- Routes ---
@bp.route("/")
def diagnostics_page():
    files = sorted(MANUAL_DIR.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    entries = []
    for f in files:
        ts = f.stem.split("_manual")[0]
        log = MANUAL_DIR / f"{ts}_manual.txt"
        png = MANUAL_DIR / f"{ts}_manual.png"
        meta = MANUAL_DIR / f"{ts}_manual.json"
        md = {}
        if meta.exists():
            try: md = json.loads(meta.read_text())
            except Exception: md = {}
        entries.append({
            "wav": f.name,
            "log": log.name if log.exists() else None,
            "png": png.name if png.exists() else None,
            "meta": md
        })
    return render_template("diagnostics/diagnostics.html",
                           files=entries, ppm=get_ppm(), gain=get_gain())

@bp.route("/check")
def diagnostics_check():
    try:
        sw = sdr_present()
        hw = sdr_device_connected() if sw else False
        return jsonify({"software": sw, "hardware": hw})
    except Exception as e:
        current_app.logger.exception("rtl_test failed")
        return jsonify({"software": False, "hardware": False, "error": str(e)})

@bp.route("/reset_ppm", methods=["POST"])
def reset_ppm_route():
    try:
        reset_ppm()
        return jsonify({"success": True, "ppm": 0})
    except Exception as e:
        current_app.logger.exception("PPM reset failed")
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route("/status")
def diagnostics_status():
    free_gb = shutil.disk_usage("/").free // (2**30)
    orphan = []
    cutoff = datetime.datetime.now().timestamp() - 3600
    for f in RECORDINGS_DIR.glob("*.iq"):
        age = f.stat().st_mtime
        entry = {"path": str(f), "size_mb": round(f.stat().st_size/(1024*1024), 2)}
        if age < cutoff:
            try:
                os.remove(f)
                entry["deleted"] = True
            except Exception as e:
                entry["delete_error"] = str(e)
        orphan.append(entry)

    return jsonify({
        "disk_free_gb": free_gb,
        "orphan_iq": orphan,
        "requirements": check_system_requirements(),
        "rtl_ppm": get_ppm(),
        "rtl_gain": get_gain()
    })
