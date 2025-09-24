@bp.route("/enable", methods=["POST"])
def enable_recordings():
    """Enable recordings, refresh TLE, and start scheduler."""
    settings = load_settings()
    if settings.get("recording_enabled"):
        return jsonify({"status": "already enabled"}), 200

    # Kill stray SDR processes before starting scheduler
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] in ('rtl_fm', 'sox'):
                proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    settings["recording_enabled"] = True
    save_settings(settings)

    # Refresh TLE and predictions before starting scheduler
    refresh_tle_and_predictions()

    # ✅ Run scheduler as a module so imports work
    subprocess.Popen(["python3", "-m", "app.utils.sdr_scheduler"])

    return jsonify({"status": "enabled"}), 200
    
