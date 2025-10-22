import os, json, shutil, subprocess, psutil, datetime
from pathlib import Path
from flask import render_template, jsonify, request, current_app, redirect, url_for, flash
from app.utils.iq_cleanup import cleanup_orphan_iq
from app.features.diagnostics import bp
from app.utils import passes as passes_utils
from app.utils.decoder import process_uploaded_wav

# --- Paths & constants ---
STATE_FILE     = Path.home() / "sstv-groundstation/current_pass.json"
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

def save_settings(s): SETTINGS_FILE.write_text(json.dumps(s, indent=2))

def get_ppm():
    try: return int(load_settings().get("rtl_ppm", 0))
    except (ValueError, TypeError): return 0

def get_gain():
    try: return str(load_settings().get("rtl_gain", "0"))
    except Exception: return "0"

def set_gain(g):
    s = load_settings(); s["rtl_gain"] = str(g); save_settings(s)

# --- System checks ---
def check_system_requirements():
    bins = [("sox","Audio conversion"),("rtl_sdr","RTL-SDR capture"),("rtl_fm","FM demod"),("rtl_power","Spectrum")]
    return [{"name":n,"desc":d,"found":bool(shutil.which(n)),"path":shutil.which(n) or "Not found"} for n,d in bins]

def sdr_present():
    """Check for rtl_sdr binary on PATH."""
    return bool(shutil.which("rtl_sdr"))

def sdr_device_connected():
    """Probe the dongle via `rtl_test -t`; returns True if hardware responds."""
    try:
        res = subprocess.run(["rtl_test","-t"], capture_output=True, text=True, timeout=3)
        out = (res.stdout or "") + (res.stderr or "")
        return any(k in out for k in ("Reading samples", "Found Rafael"))
    except Exception:
        return False

def sdr_in_use():
    for proc in psutil.process_iter(['name','cmdline']):
        try:
            if (proc.info['name'] and 'rtl_fm' in proc.info['name']) or \
               (proc.info['cmdline'] and any('rtl_fm' in c for c in proc.info['cmdline'])):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def scheduled_pass_soon(minutes=5):
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        for p in passes_utils.load_predictions():
            aos = datetime.datetime.fromisoformat(p['aos'])
            if now <= aos <= now + datetime.timedelta(minutes=minutes):
                return True
    except Exception:
        pass
    return False

# --- Routes ---
@bp.route("/")
def diagnostics_page():
    # Precompute manual entries for template (avoid Path.exists in Jinja)
    files = sorted(MANUAL_DIR.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
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
    return render_template("diagnostics/diagnostics.html", files=entries, ppm=get_ppm(), gain=get_gain())

@bp.route("/check")
def diagnostics_check():
    try:
        r = subprocess.run(["rtl_test","-t"],capture_output=True,text=True,timeout=5)
        out = (r.stdout or "") + (r.stderr or "")
        return jsonify({"success": any(x in out for x in ("Reading samples","Found Rafael")), "output": out})
    except Exception as e:
        current_app.logger.exception("rtl_test failed")
        return jsonify({"success": False, "output": str(e)})

@bp.route("/status")
def diagnostics_status():
    free_gb = shutil.disk_usage("/").free // (2**30)
    pass_info, orphan = None, []

    if STATE_FILE.exists():
        try:
            pass_info = json.loads(STATE_FILE.read_text())
            iq = pass_info.get("iq_file")
            if iq and os.path.exists(iq):
                pass_info["iq_size_mb"] = round(os.path.getsize(iq)/(1024*1024), 2)
        except Exception as e:
            current_app.logger.exception("Failed reading state file")
            pass_info = {"error": f"Could not read pass state: {e}"}

    for f in RECORDINGS_DIR.glob("*.iq"):
        if not pass_info or str(f) != pass_info.get("iq_file"):
            entry = {"path": str(f), "size_mb": round(f.stat().st_size/(1024*1024), 2)}
            if free_gb < LOW_SPACE_GB:
                try: os.remove(f); entry["deleted"] = True
                except Exception as e: entry["delete_error"] = str(e)
            orphan.append(entry)

    return jsonify({
        "disk_free_gb": free_gb,
        "pass_info": pass_info,
        "orphan_iq": orphan,
        "requirements": check_system_requirements(),
        "rtl_ppm": get_ppm(),
        "rtl_gain": get_gain()
    })

@bp.route("/clear_all_iq", methods=["POST"])
def clear_all_iq():
    return jsonify({"success": True, "deleted": cleanup_orphan_iq()})

@bp.route("/delete_iq", methods=["POST"])
def delete_iq():
    try:
        path = request.get_json().get("path")
        if path and os.path.exists(path) and path.endswith(".iq"):
            os.remove(path)
            return jsonify({"success": True, "message": f"Deleted {path}"})
        return jsonify({"success": False, "message": "File not found"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@bp.route("/sdr/status")
def sdr_status():
    if not sdr_present(): return jsonify({"status": "grey", "reason": "binary missing"})
    if sdr_in_use():      return jsonify({"status": "red", "reason": "rtl_fm busy"})
    if scheduled_pass_soon(): return jsonify({"status": "amber", "reason": "scheduled soon"})
    return jsonify({"status": "green", "reason": "ready"})

@bp.route("/calibrate", methods=["POST"])
def calibrate():
    try:
        CAL_DIR = RECORDINGS_DIR / "calibration"
        CAL_DIR.mkdir(parents=True, exist_ok=True)
        fm_csv = CAL_DIR / "scan_fm.csv"
        subprocess.run(
            ["rtl_power","-f","88M:108M:100k","-g","20","-e","6",str(fm_csv)],
            check=True
        )

        # Parse CSV for strongest peak
        best_freq, best_power = None, -1e9
        for line in fm_csv.read_text().splitlines():
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

        expected = round(best_freq/100_000)*100_000
        ppm = int(round(((best_freq-expected)/expected)*1e6))
        ppm = max(min(ppm, 3000), -3000)

        settings = load_settings()
        settings["rtl_ppm"] = ppm
        save_settings(settings)

        def nf_capture(label, ppm_arg=None):
            rate, png = 48000, IMAGES_DIR / f"calibration_{label}.png"
            ppm_opts = ["-p", str(ppm_arg)] if ppm_arg is not None else []
            cmd = [
                "timeout","8","rtl_fm","-f",str(expected),"-M","fm","-s",str(rate),
                "-g","29.7","-l","0"
            ] + ppm_opts
            p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(
                ["sox","-t","raw","-r",str(rate),"-e","signed","-b","16","-c","1","-",
                 "-n","spectrogram","-o",str(png)],
                stdin=p1.stdout
            )
            p1.stdout.close()
            p2.wait()
            return png.name

        return jsonify({
            "success": True,
            "measured_hz": int(best_freq),
            "expected_hz": int(expected),
            "ppm": ppm,
            "png_before": nf_capture("before"),
            "png_after": nf_capture("after", ppm)
        })
    except Exception as e:
        current_app.logger.exception("Calibration failed")
        return jsonify({"success": False, "error": str(e)}), 500


# --- Manual Recorder ---
@bp.route("/recorder", methods=["GET","POST"])
def manual_recorder():
    try:
        files = sorted(MANUAL_DIR.glob("*.wav"), key=os.path.getmtime, reverse=True)
        ppm   = get_ppm()
        gain  = get_gain()
    except Exception as e:
        current_app.logger.exception("Failed to load manual recordings or PPM")
        flash(f"Error loading manual recordings: {e}", "danger")
        files, ppm, gain = [], 0, "0"

    if request.method == "POST":
        duration  = int(request.form.get("duration", 30))
        freq      = request.form.get("frequency", "145.800M")
        ppm_arg   = request.form.get("ppm", str(ppm))
        gain_arg  = request.form.get("gain", get_gain())
        set_gain(gain_arg)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_file  = MANUAL_DIR / f"{timestamp}_manual.wav"
        log_file  = MANUAL_DIR / f"{timestamp}_manual.txt"
        meta_file = MANUAL_DIR / f"{timestamp}_manual.json"

        # DEMO branch if no dongle connected
        if not sdr_device_connected():
            demo_file = MANUAL_DIR / f"{timestamp}_demo_manual.wav"
            flash(f"Writing DEMO to: {demo_file.resolve()}", "info")
            try:
                segs = []
                for i in range(int(duration*2)):
                    freq_tone = 440 if (i % 2 == 0) else 880
                    seg = MANUAL_DIR / f"{timestamp}_seg{i}.wav"
                    subprocess.run(
                        ["sox","-n",str(seg),"synth","0.5","sin",str(freq_tone)],
                        check=True
                    )
                    segs.append(str(seg))
                subprocess.run(["sox"] + segs + [str(demo_file)], check=True)
                for s in segs: os.remove(s)
                flash(f"Demo recording created: {demo_file.name}", "success")
            except Exception as e:
                current_app.logger.exception("Demo recording failed")
                flash(f"Demo error: {e}", "danger")
            return redirect(url_for("diagnostics.manual_recorder"))

        # REAL SDR branch
        SAMPLE_RATE = "48000"
        flash(f"Recording to: {wav_file.resolve()} (Gain {gain_arg}, PPM {ppm_arg})", "info")

        with open(log_file, "w") as lf:
            try:
                cmd = ["rtl_fm","-M","fm","-f",freq,"-p",ppm_arg,"-s",SAMPLE_RATE]
                cmd += ["-g", gain_arg]
                p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=lf)
                p2 = subprocess.Popen(
                    ["sox","-t","raw","-r",SAMPLE_RATE,"-e","signed","-b","16","-c","1","-", str(wav_file)],
                    stdin=p1.stdout, stderr=lf
                )
                p1.stdout.close()
                p2.wait(timeout=duration+5)
            except subprocess.TimeoutExpired:
                p1.terminate(); p2.terminate()
                flash("Recording timed out", "danger")
            finally:
                if p1.poll() is None: p1.terminate()
                if p2.poll() is None: p2.terminate()

        # Write metadata JSON
        meta = {
            "frequency": freq,
            "duration": duration,
            "ppm": ppm_arg,
            "gain": gain_arg,
            "wav": wav_file.name,
            "log": log_file.name
        }
        try: meta_file.write_text(json.dumps(meta, indent=2))
        except Exception as e: current_app.logger.warning(f"Failed to write meta: {e}")

        flash(f"Recording complete: {wav_file.name} (Gain {gain_arg}, PPM {ppm_arg})", "success")
        return redirect(url_for("diagnostics.manual_recorder"))

    # GET → render form + list
    return render_template("diagnostics/diagnostics.html", files=files, ppm=ppm, gain=gain)

# --- Endpoints for orphan IQ cleanup already above ---

# You already have /sdr/status defined in part 1

# The manual recorder route is in part 2

# If you want to add a simple decoder hook for uploaded WAVs, you can keep it here:
@bp.route("/decode_upload", methods=["POST"])
def decode_upload():
    """Optional: allow user to upload a WAV and run decoder."""
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
