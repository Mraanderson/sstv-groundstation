import os, json, shutil, subprocess, psutil, datetime
from pathlib import Path
from flask import render_template, jsonify, request, current_app, redirect, url_for, flash, send_from_directory, abort
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
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

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

# --- Simple requirements checker used by diagnostics/status ---
def check_system_requirements():
    tools = ["rtl_sdr", "rtl_fm", "rtl_power", "sox"]
    return {t: bool(shutil.which(t)) for t in tools}

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
            try:
                md = json.loads(meta.read_text())
            except Exception:
                md = {}
        entries.append({
            "wav": f.name,
            "wav_path": str(f),
            "log": log.name if log.exists() else None,
            "png": png.name if png.exists() else None,
            "meta": md,
            "meta_filename": meta.name if meta.exists() else None
        })

    # try to offer a calibration frequency guess from the last calibration CSV if present
    cal_guess = "145.800M"
    try:
        cal_csv = RECORDINGS_DIR / "calibration" / "scan_fm.csv"
        if cal_csv.exists():
            best_freq = None
            for line in cal_csv.read_text().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 7:
                    continue
                f_start, f_end = float(parts[2]), float(parts[3])
                bins = [float(x) for x in parts[6:] if x]
                if not bins:
                    continue
                idx, power = max(enumerate(bins), key=lambda kv: kv[1])
                bin_size = (f_end - f_start) / len(bins)
                candidate = f_start + (idx + 0.5) * bin_size
                if best_freq is None or power > 0:
                    best_freq = candidate
            if best_freq:
                cal_guess = f"{best_freq/1_000_000:.3f}M"
    except Exception:
        current_app.logger.debug("calibration guess unavailable")

    return render_template("diagnostics/diagnostics.html",
                           files=entries, ppm=get_ppm(), gain=get_gain(), cal_guess=cal_guess)

# new helper to serve manual files (inline for images if ?attachment=0, otherwise attachment)
@bp.route("/manual/file/<path:filename>")
def download_manual_file(filename):
    try:
        safe = Path(filename).name
        attach = request.args.get("attachment", "1") == "1"
        return send_from_directory(str(MANUAL_DIR), safe, as_attachment=attach)
    except Exception:
        current_app.logger.exception("download_manual_file failed")
        abort(404)

# delete manual recording (works with form POST or AJAX)
@bp.route("/manual/delete", methods=["POST"])
def delete_manual():
    fname = request.form.get("filename") or (request.json and request.json.get("filename"))
    if not fname:
        return jsonify({"success": False, "error": "missing filename"}), 400
    base = Path(fname).stem.split("_manual")[0]
    removed = []
    errors = []
    for p in MANUAL_DIR.glob(f"{base}_manual*"):
        try:
            p.unlink()
            removed.append(p.name)
        except Exception as e:
            current_app.logger.exception("Failed to delete manual file")
            errors.append(f"{p.name}: {e}")
    if errors:
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "removed": removed, "errors": errors}), 500
        flash("Some files could not be deleted: " + "; ".join(errors), "warning")
    else:
        flash("Deleted: " + ", ".join(removed), "success")
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "removed": removed})
    return redirect(url_for("diagnostics.manual_recorder"))

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
    try:
        # Query disk usage for the recordings path (falls back to project cwd)
        target_path = RECORDINGS_DIR.resolve() if RECORDINGS_DIR.exists() else Path(".").resolve()
        usage = shutil.disk_usage(str(target_path))
        free_gb = round(usage.free / (1024 ** 3), 2)
        enough = free_gb >= LOW_SPACE_GB

        return jsonify({
            "disk_free_gb": free_gb,
            "enough_space": enough,
            "requirements": check_system_requirements(),
            "rtl_ppm": get_ppm(),
            "rtl_gain": get_gain()
        })
    except Exception as e:
        current_app.logger.exception("diagnostics_status failed")
        return jsonify({
            "disk_free_gb": None,
            "enough_space": False,
            "requirements": check_system_requirements(),
            "rtl_ppm": get_ppm(),
            "rtl_gain": get_gain(),
            "error": str(e)
        }), 200

@bp.route("/calibrate", methods=["POST"])
def calibrate():
    try:
        CAL_DIR = RECORDINGS_DIR / "calibration"
        CAL_DIR.mkdir(parents=True, exist_ok=True)
        fm_csv = CAL_DIR / "scan_fm.csv"

        # Scan FM band for strong signal
        subprocess.run(
            ["rtl_power", "-f", "88M:108M:100k", "-g", "20", "-e", "6", str(fm_csv)],
            check=True
        )

        # Parse CSV for strongest peak
        best_freq, best_power = None, -1e9
        lines = fm_csv.read_text().splitlines()
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 7: continue
            f_start, f_end = float(parts[2]), float(parts[3])
            bins = [float(x) for x in parts[6:] if x]
            if not bins: continue
            idx, power = max(enumerate(bins), key=lambda kv: kv[1])
            if power > best_power:
                best_power = power
                bin_size = (f_end - f_start) / len(bins)
                best_freq = f_start + (idx + 0.5) * bin_size

        if not best_freq:
            return jsonify({"success": False, "error": "No strong FM peak found"})

        expected = round(best_freq / 100_000) * 100_000
        ppm = int(round(((best_freq - expected) / expected) * 1e6))
        ppm = max(min(ppm, 3000), -3000)

        settings = load_settings()
        settings["rtl_ppm"] = ppm
        save_settings(settings)

        def nf_capture(label, ppm_arg=None):
            rate, png = 48000, IMAGES_DIR / f"calibration_{label}.png"
            ppm_opts = ["-p", str(ppm_arg)] if ppm_arg is not None else []
            cmd = [
                "timeout", "8", "rtl_fm", "-f", str(expected), "-M", "fm", "-s", str(rate),
                "-g", "29.7", "-l", "0"
            ] + ppm_opts
            p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(
                ["sox", "-t", "raw", "-r", str(rate), "-e", "signed", "-b", "16", "-c", "1", "-",
                 "-n", "spectrogram", "-o", str(png)],
                stdin=p1.stdout
            )
            p1.stdout.close()
            p2.wait()
            return png.name

        return jsonify({
            "success": True,
            "timestamp": datetime.datetime.now().isoformat(),
            "measured_hz": int(best_freq),
            "expected_hz": int(expected),
            "ppm": ppm,
            "csv_preview": lines[:5],
            "png_before": nf_capture("before"),
            "png_after": nf_capture("after", ppm)
        })
    except Exception as e:
        current_app.logger.exception("Calibration failed")
        return jsonify({"success": False, "error": str(e)}), 500
        
@bp.route("/recorder", methods=["GET", "POST"])
def manual_recorder():
    try:
        files = sorted(MANUAL_DIR.glob("*.wav"), key=os.path.getmtime, reverse=True)[:5]
        ppm = get_ppm()
        gain = get_gain()
    except Exception as e:
        current_app.logger.exception("Failed to load manual recordings or PPM")
        flash(f"Error loading manual recordings: {e}", "danger")
        files, ppm, gain = [], 0, "0"

    if request.method == "POST":
        duration = int(request.form.get("duration", 30))
        freq = request.form.get("frequency", "145.800M")
        ppm_arg = request.form.get("ppm", str(ppm))  # use provided ppm or current setting
        gain_arg = request.form.get("gain", get_gain())
        set_gain(gain_arg)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_file = MANUAL_DIR / f"{timestamp}_manual.wav"
        log_file = MANUAL_DIR / f"{timestamp}_manual.txt"
        meta_file = MANUAL_DIR / f"{timestamp}_manual.json"
        png_file = MANUAL_DIR / f"{timestamp}_manual.png"

        if not sdr_device_connected():
            demo_file = MANUAL_DIR / f"{timestamp}_demo_manual.wav"
            flash(f"No dongle detected — running DEMO to: {demo_file.name}", "warning")
            try:
                segs = []
                for i in range(int(duration * 2)):
                    freq_tone = 440 if (i % 2 == 0) else 880
                    seg = MANUAL_DIR / f"{timestamp}_seg{i}.wav"
                    subprocess.run(["sox", "-n", str(seg), "synth", "0.5", "sin", str(freq_tone)], check=True)
                    segs.append(str(seg))
                subprocess.run(["sox"] + segs + [str(demo_file)], check=True)
                for s in segs: os.remove(s)
                flash(f"Demo recording created: {demo_file.name}", "success")
            except Exception as e:
                current_app.logger.exception("Demo recording failed")
                flash(f"Demo error: {e}", "danger")
            return redirect(url_for("diagnostics.manual_recorder"))

        SAMPLE_RATE = "48000"
        flash(f"Recording to: {wav_file.name} (Gain {gain_arg}, PPM {ppm_arg})", "info")

        success = False
        p1 = p2 = None
        with open(log_file, "w") as lf:
            try:
                cmd1 = ["rtl_fm", "-M", "fm", "-f", freq, "-p", str(ppm_arg), "-s", SAMPLE_RATE, "-g", gain_arg]
                cmd2 = ["sox", "-t", "raw", "-r", SAMPLE_RATE, "-e", "signed", "-b", "16", "-c", "1", "-", str(wav_file)]
                p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=lf)
                p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stderr=lf)
                p1.stdout.close()
                p2.wait(timeout=duration + 5)
                success = True
            except subprocess.TimeoutExpired:
                flash("Recording timed out", "danger")
                if p1: p1.terminate()
                if p2: p2.terminate()
            finally:
                try:
                    if p1 and p1.poll() is None: p1.terminate()
                    if p2 and p2.poll() is None: p2.terminate()
                except Exception:
                    pass

        meta = {
            "frequency": freq,
            "duration": duration,
            "ppm": ppm_arg,
            "gain": gain_arg,
            "wav": wav_file.name,
            "log": log_file.name
        }
        try:
            meta_file.write_text(json.dumps(meta, indent=2))
        except Exception as e:
            current_app.logger.warning(f"Failed to write meta: {e}")

        # generate spectrogram image for the wav (best effort)
        if success:
            try:
                subprocess.run(["sox", str(wav_file), "-n", "spectrogram", "-o", str(png_file)], check=True, timeout=20)
                # update meta with png name if created
                if png_file.exists():
                    meta["png"] = png_file.name
                    try: meta_file.write_text(json.dumps(meta, indent=2))
                    except Exception: current_app.logger.debug("Could not update meta with png")
            except Exception as e:
                current_app.logger.debug("Spectrogram creation failed: %s", e)

        if success:
            flash(f"Recording complete: {wav_file.name} (Gain {gain_arg}, PPM {ppm_arg})", "success")

        return redirect(url_for("diagnostics.manual_recorder"))

    return render_template("diagnostics/diagnostics.html", files=files, ppm=ppm, gain=gain)

@bp.route("/decode_upload", methods=["POST"])
def decode_upload():
    try:
        file = request.files.get("file")
        if not file or not file.filename.endswith(".wav"):
            return jsonify({"success": False, "error": "No WAV file provided"}), 400

        save_path = MANUAL_DIR / file.filename
        file.save(save_path)

        result = process_uploaded_wav(save_path)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        current_app.logger.exception("Decode upload failed")
        return jsonify({"success": False, "error": str(e)}), 500
        
@bp.route("/sdr/status")
def sdr_status():
    try:
        if not sdr_present():
            return jsonify({"status": "grey", "reason": "SDR software not found"})
        if sdr_in_use():
            return jsonify({"status": "red", "reason": "SDR currently in use"})
        if hasattr(passes_utils, "scheduled_pass_soon") and passes_utils.scheduled_pass_soon():
            return jsonify({"status": "amber", "reason": "Scheduled pass approaching"})
        if sdr_device_connected():
            return jsonify({"status": "green", "reason": "SDR ready"})
        return jsonify({"status": "grey", "reason": "SDR hardware not detected"})
    except Exception as e:
        current_app.logger.exception("sdr_status failed")
        return jsonify({"status": "grey", "reason": f"Error: {e}"}), 500