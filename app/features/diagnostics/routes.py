import os, json, shutil, subprocess
from pathlib import Path
from flask import render_template, jsonify, request
from app.utils.iq_cleanup import cleanup_orphan_iq
from app.features.diagnostics import bp

STATE_FILE = os.path.expanduser("~/sstv-groundstation/current_pass.json")
RECORDINGS_DIR, LOW_SPACE_GB = Path("recordings"), 2
SETTINGS_FILE = Path("settings.json")

def load_settings():
    return json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}
def save_settings(s): SETTINGS_FILE.write_text(json.dumps(s, indent=2))

def check_system_requirements():
    bins=[("sox","Audio conversion"),("rtl_sdr","RTL-SDR capture")]
    return [{"name":n,"desc":d,"found":bool(shutil.which(n)),"path":shutil.which(n) or "Not found"} for n,d in bins]

@bp.route("/")
def diagnostics_page(): return render_template("diagnostics/diagnostics.html")

@bp.route("/check")
def diagnostics_check():
    try:
        r=subprocess.run(["rtl_test","-t"],capture_output=True,text=True,timeout=5)
        out=r.stdout+r.stderr
        return jsonify({"success":any(x in out for x in("Reading samples","Found Rafael")),"output":out})
    except Exception as e: return jsonify({"success":False,"output":str(e)})

@bp.route("/status")
def diagnostics_status():
    free_gb=shutil.disk_usage("/").free//(2**30)
    pass_info=None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f: pass_info=json.load(f)
            iq=pass_info.get("iq_file")
            if iq and os.path.exists(iq): pass_info["iq_size_mb"]=round(os.path.getsize(iq)/(1024*1024),2)
        except Exception as e: pass_info={"error":f"Could not read pass state: {e}"}
    orphan=[]
    for f in RECORDINGS_DIR.glob("*.iq"):
        if not pass_info or str(f)!=pass_info.get("iq_file"):
            entry={"path":str(f),"size_mb":round(f.stat().st_size/(1024*1024),2)}
            if free_gb<LOW_SPACE_GB:
                try: os.remove(f); entry["deleted"]=True
                except Exception as e: entry["delete_error"]=str(e)
            orphan.append(entry)
    return jsonify({"disk_free_gb":free_gb,"pass_info":pass_info,"orphan_iq":orphan,"requirements":check_system_requirements()})

@bp.route("/clear_all_iq",methods=["POST"])
def clear_all_iq(): return jsonify({"success":True,"deleted":cleanup_orphan_iq()})

@bp.route("/delete_iq",methods=["POST"])
def delete_iq():
    try:
        path=request.get_json().get("path")
        if path and os.path.exists(path) and path.endswith(".iq"):
            os.remove(path); return jsonify({"success":True,"message":f"Deleted {path}"})
        return jsonify({"success":False,"message":"File not found"})
    except Exception as e: return jsonify({"success":False,"message":str(e)})

# --- Calibration route ---
@bp.route("/calibrate", methods=["POST"])
def calibrate():
    CAL_DIR=(RECORDINGS_DIR/"calibration"); CAL_DIR.mkdir(parents=True,exist_ok=True)
    fm_csv,fm_png=CAL_DIR/"scan_fm.csv",CAL_DIR/"scan_fm.png"

    # Scan FM band
    subprocess.run(["rtl_power","-f","88M:108M:100k","-g","20","-e","6",str(fm_csv)],check=True)

    # Parse CSV for strongest peak
    best_freq,best_power=None,-1e9
    with open(fm_csv) as f:
        for line in f:
            parts=line.strip().split(",")
            if len(parts)<7: continue
            f_start,f_end=float(parts[0]),float(parts[1]); bins=[float(x) for x in parts[6:]]
            if not bins: continue
            idx=max(range(len(bins)),key=lambda i:bins[i]); power=bins[idx]
            if power>best_power:
                best_power=power; bin_size=(f_end-f_start)/len(bins)
                best_freq=f_start+(idx+0.5)*bin_size
    if not best_freq: return jsonify({"success":False,"error":"No strong FM peak found"})

    expected=round(best_freq/100_000)*100_000
    ppm=int(round(((best_freq-expected)/expected)*1e6)); ppm=max(min(ppm,3000),-3000)

    def nf_capture(label,ppm_arg=None):
        rate=48000; wav,png=CAL_DIR/f"{label}.wav",CAL_DIR/f"{label}.png"
        ppm_opts=["-p",str(ppm_arg)] if ppm_arg is not None else []
        cmd=f"timeout 8 rtl_fm -f {expected} -M fm -s {rate} -g 29.7 -l 0 {' '.join(ppm_opts)} " \
            f"| tee >(sox -t raw -r {rate} -e signed -b 16 -c 1 - -n spectrogram -o {png}) " \
            f"| sox -t raw -r {rate} -e signed -b 16 -c 1 - {wav}"
        subprocess.run(cmd,shell=True,check=True); return wav.name,png.name

    wav_before,png_before=nf_capture("before")
    wav_after,png_after=nf_capture("after",ppm)

    settings=load_settings(); settings["rtl_ppm"]=ppm; save_settings(settings)

    return jsonify({"success":True,"measured_hz":int(best_freq),"expected_hz":int(expected),
                    "ppm":ppm,"scan_csv":fm_csv.name,
                    "wav_before":wav_before,"png_before":png_before,
                    "wav_after":wav_after,"png_after":png_after})
    
