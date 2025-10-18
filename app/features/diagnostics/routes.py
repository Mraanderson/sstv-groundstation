import os, json, shutil, subprocess, psutil, datetime, time
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
    return json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}

def save_settings(s): SETTINGS_FILE.write_text(json.dumps(s, indent=2))

def get_ppm():
    try: return int(load_settings().get("rtl_ppm", 0))
    except (ValueError, TypeError): return 0

# --- System checks ---
def check_system_requirements():
    bins = [("sox","Audio conversion"),("rtl_sdr","RTL-SDR capture")]
    return [{"name":n,"desc":d,"found":bool(shutil.which(n)),"path":shutil.which(n) or "Not found"} for n,d in bins]

#def sdr_present(): return shutil.which("rtl_sdr") is not None
def sdr_present(): 
    """Check for rtl_sdr binary on $PATH."""
    return bool(shutil.which("rtl_sdr"))

def sdr_device_connected():
    """Probe the dongle via `rtl_test -t`; returns True if hardware responds."""
    try:
        res = subprocess.run(
            ["rtl_test", "-t"], capture_output=True, text=True, timeout=3
        )
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
        except (psutil.NoSuchProcess, psutil.AccessDenied): continue
    return False

def scheduled_pass_soon(minutes=5):
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        for p in passes_utils.load_predictions():
            aos = datetime.datetime.fromisoformat(p['aos'])
            if now <= aos <= now + datetime.timedelta(minutes=minutes):
                return True
    except Exception: pass
    return False

# --- Routes ---
@bp.route("/")
def diagnostics_page(): return render_template("diagnostics/diagnostics.html")

@bp.route("/check")
def diagnostics_check():
    try:
        r = subprocess.run(["rtl_test","-t"],capture_output=True,text=True,timeout=5)
        out = r.stdout + r.stderr
        return jsonify({"success": any(x in out for x in ("Reading samples","Found Rafael")), "output": out})
    except Exception as e:
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
        "rtl_ppm": get_ppm()
    })

@bp.route("/clear_all_iq", methods=["POST"])
def clear_all_iq(): return jsonify({"success": True, "deleted": cleanup_orphan_iq()})

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

@bp.route("/calibrate", methods=["POST"])
def calibrate():
    try:
        CAL_DIR = RECORDINGS_DIR / "calibration"; CAL_DIR.mkdir(parents=True, exist_ok=True)
        fm_csv = CAL_DIR / "scan_fm.csv"
        subprocess.run(["rtl_power","-f","88M:108M:100k","-g","20","-e","6",str(fm_csv)], check=True)

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

        if not best_freq: return jsonify({"success": False, "error": "No strong FM peak found"})
        expected = round(best_freq/100_000)*100_000
        ppm = int(round(((best_freq-expected)/expected)*1e6))
        ppm = max(min(ppm, 3000), -3000)

        settings = load_settings(); settings["rtl_ppm"] = ppm; save_settings(settings)

        def nf_capture(label, ppm_arg=None):
            rate, png = 48000, IMAGES_DIR / f"calibration_{label}.png"
            ppm_opts = ["-p", str(ppm_arg)] if ppm_arg is not None else []
            cmd = f"timeout 8 rtl_fm -f {expected} -M fm -s {rate} -g 29.7 -l 0 {' '.join(ppm_opts)} " \
                  f"| sox -t raw -r {rate} -e signed -b 16 -c 1 - -n spectrogram -o {png}"
            subprocess.run(cmd, shell=True, check=True)
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

@bp.route("/sdr/status")
def sdr_status():
    if not sdr_present(): return jsonify({"status": "grey"})
    if sdr_in_use():      return jsonify({"status": "red"})
    if scheduled_pass_soon(): return jsonify({"status": "amber"})
    return jsonify({"status": "green"})

# --- System checks (add this above your routes) ---
def sdr_device_connected():
    """Returns True only if rtl_test -t actually finds a dongle."""
    try:
        res = subprocess.run(
            ["rtl_test", "-t"], capture_output=True, text=True, timeout=3
        )
        out = (res.stdout or "") + (res.stderr or "")
        return any(x in out for x in ("Reading samples", "Found Rafael"))
    except Exception:
        return False

# --- Manual Recorder ---
@bp.route("/recorder", methods=["GET", "POST"])
def manual_recorder():
    try:
        files = sorted(MANUAL_DIR.glob("*.wav"), key=os.path.getmtime, reverse=True)
        ppm   = get_ppm()
    except Exception as e:
        current_app.logger.exception("Failed to load manual recordings or PPM")
        flash(f"Error loading manual recordings: {e}", "danger")
        files, ppm = [], 0

    if request.method == "POST":
        duration  = int(request.form.get("duration", 30))
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # DEMO branch if no dongle actually connected
        if not sdr_device_connected():
            demo_file = MANUAL_DIR / f"{timestamp}_demo_manual.wav"

            # debug flash to show where it writes
            flash(f"Writing DEMO to: {demo_file.resolve()}", "info")

            try:
                # build 0.5s tone segments
                segs = []
                for i in range(int(duration * 2)):
                    freq = 440 if (i % 2 == 0) else 880
                    seg = MANUAL_DIR / f"{timestamp}_seg{i}.wav"
                    subprocess.run(
                        ["sox", "-n", str(seg), "synth", "0.5", "sin", str(freq)],
                        check=True
                    )
                    segs.append(str(seg))

                # concatenate them
                subprocess.run(["sox"] + segs + [str(demo_file)], check=True)

                # cleanup
                for s in segs: os.remove(s)

                flash(f"Demo recording created: {demo_file.name}", "success")
            except Exception as e:
                current_app.logger.exception("Demo recording failed")
                flash(f"Demo error: {e}", "danger")

            return redirect(url_for("diagnostics.manual_recorder"))

        # REAL SDR branch
        freq       = request.form.get("frequency", "145.800M")
        ppm_arg    = request.form.get("ppm", str(ppm))
        SAMPLE_RATE= "48000"
        wav_file   = MANUAL_DIR / f"{timestamp}_manual.wav"
        log_file   = MANUAL_DIR / f"{timestamp}_manual.txt"

        # debug flash
        flash(f"Writing REAL to: {wav_file.resolve()}", "info")

        with open(log_file, "w") as lf:
            try:
                p1 = subprocess.Popen(
                    ["rtl_fm","-M","fm","-f",freq,"-p",ppm_arg,"-s",SAMPLE_RATE,"-g","40"],
                    stdout=subprocess.PIPE, stderr=lf
                )
                p2 = subprocess.Popen(
                    ["sox","-t","raw","-r",SAMPLE_RATE,"-e","s16","-b","16","-c","1","-",
                     str(wav_file)],
                    stdin=p1.stdout, stderr=lf
                )
                p1.stdout.close()
                p2.wait(timeout=duration + 5)
            except subprocess.TimeoutExpired:
                p1.terminate(); p2.terminate()
                flash("Recording timed out", "danger")
            finally:
                if p1.poll() is None: p1.terminate()
                if p2.poll() is None: p2.terminate()

        # soxi analysis & decode...
        # (keep your existing soxi + process_uploaded_wav here)

        flash(f"Recording complete: {wav_file.name}", "success")
        return redirect(url_for("diagnostics.manual_recorder"))

    # GET → render form + list
    return render_template("diagnostics/manual_recorder.html", files=files, ppm=ppm)
