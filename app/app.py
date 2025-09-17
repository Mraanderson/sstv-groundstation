from flask import Flask, render_template, send_from_directory, request, redirect, url_for
import os, json, requests
from datetime import datetime, timedelta, timezone
from skyfield.api import Loader, wgs84, EarthSatellite

app = Flask(__name__)
IMAGES_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'images'))
TLE_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'tle'))
CONFIG_FILE = os.path.join(app.root_path, 'config.json')
TLE_FILE = os.path.join(TLE_DIR, "iss__zarya_.txt")

def get_all_images():
    imgs = []
    for root, _, files in os.walk(IMAGES_DIR):
        for f in files:
            if f.lower().endswith(('.png','.jpg','.jpeg','.gif','.bmp','.webp')):
                rel_dir = os.path.relpath(root, IMAGES_DIR)
                rel_path = os.path.join(rel_dir, f) if rel_dir != '.' else f
                imgs.append(rel_path.replace("\\","/"))
    return sorted(imgs)

def config_exists_and_valid():
    if not os.path.exists(CONFIG_FILE): return False
    try:
        with open(CONFIG_FILE) as f: cfg = json.load(f)
        for k in ["location_lat","location_lon","location_alt","timezone"]:
            if not cfg.get(k): return False
        return True
    except: return False

def get_tle_last_updated():
    if os.path.exists(TLE_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(TLE_FILE), tz=timezone.utc)
        return mtime.strftime("%Y-%m-%d %H:%M:%S UTC")
    return "Never"

def fetch_latest_tle():
    os.makedirs(TLE_DIR, exist_ok=True)
    r = requests.get("https://celestrak.org/NORAD/elements/stations.txt", timeout=10)
    r.raise_for_status()
    lines = r.text.strip().splitlines()
    for i in range(len(lines)):
        if lines[i].upper().startswith("ISS"):
            with open(TLE_FILE,"w") as f: f.write("\n".join(lines[i:i+3])+"\n")
            return True
    return False

def tle_needs_refresh(max_age_days=3):
    if not os.path.exists(TLE_FILE): return True
    mtime = datetime.fromtimestamp(os.path.getmtime(TLE_FILE), tz=timezone.utc)
    return (datetime.now(timezone.utc)-mtime).total_seconds()/86400.0 > max_age_days

@app.route("/images/<path:filename>")
def serve_image(filename): return send_from_directory(IMAGES_DIR, filename)

@app.route("/") 
@app.route("/gallery")
def gallery(): return render_template("gallery.html", image_names=get_all_images())

@app.route("/config", methods=["GET","POST"])
def config_page():
    keys = ["location_lat","location_lon","location_alt","timezone","show_local_time"]
    msg = None
    if request.method=="POST":
        cfg = {}
        for k in keys:
            cfg[k] = request.form.get(k)=="on" if k=="show_local_time" else request.form.get(k,"")
        with open(CONFIG_FILE,"w") as f: json.dump(cfg,f,indent=4)
        msg = "Configuration updated successfully."
    cfg_data = {k:"" for k in keys}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: cfg_data = json.load(f)
    return render_template("config.html", config_data=cfg_data, message=msg)

@app.route("/update-tle", methods=["POST"])
def update_tle():
    try: msg = "TLE updated successfully." if fetch_latest_tle() else "ISS TLE not found in source."
    except Exception as e: msg = f"Error updating TLE: {e}"
    return redirect(url_for('passes_page'))

@app.route("/set-time-display", methods=["POST"])
def set_time_display():
    data = request.get_json()
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: cfg = json.load(f)
    cfg["show_local_time"] = bool(data.get("show_local_time", False))
    with open(CONFIG_FILE,"w") as f: json.dump(cfg,f,indent=4)
    return ("",204)

@app.route("/passes")
def passes_page():
    if not config_exists_and_valid(): return redirect(url_for('config_page'))
    if tle_needs_refresh():
        try: fetch_latest_tle()
        except Exception as e: return render_template("passes.html", passes=[], message=f"TLE refresh failed: {e}", tle_last_updated=get_tle_last_updated())
    with open(CONFIG_FILE) as f: cfg = json.load(f)
    lat, lon, alt = float(cfg.get("location_lat",0)), float(cfg.get("location_lon",0)), float(cfg.get("location_alt",0))
    show_local_time = bool(cfg.get("show_local_time", False))
    with open(TLE_FILE) as f: name,l1,l2 = f.read().strip().splitlines()[:3]
    ts = Loader('./skyfield_data').timescale()
    observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)
    sat = EarthSatellite(l1,l2,name,ts)
    tle_epoch_dt = sat.epoch.utc_datetime().replace(tzinfo=timezone.utc)
    tle_age_days = (datetime.now(timezone.utc)-tle_epoch_dt).total_seconds()/86400.0
    info = {"tle_epoch_utc": tle_epoch_dt.strftime("%Y-%m-%d %H:%M:%S"),"tle_age_days": round(tle_age_days,2),"observer":{"lat":lat,"lon":lon,"alt_m":alt},"min_elev_deg":0.0}
    warn = "TLE is older than 7 days — refresh from CelesTrak." if tle_age_days>7 else None
    now, end_time = datetime.now(timezone.utc), datetime.now(timezone.utc)+timedelta(hours=24)
    passes = []
    try:
        t, events = sat.find_events(observer, ts.from_datetime(now), ts.from_datetime(end_time), altitude_degrees=info["min_elev_deg"])
    except Exception as e:
        return render_template("passes.html", passes=[], message=f"Error finding passes: {e}", info=info, tle_last_updated=get_tle_last_updated(), show_local_time=show_local_time)
    current_pass = {}
    for ti, event in zip(t, events):
        if event==0: current_pass={"satellite":"ISS (ZARYA)","aos":ti.utc_datetime()}
        elif event==1: current_pass["max_elev"]=(sat-observer).at(ti).altaz()[0].degrees
        elif event==2:
            current_pass["los"]=ti.utc_datetime()
            if "aos" in current_pass and "los" in current_pass:
                current_pass["duration"]=(current_pass["los"]-current_pass["aos"]).seconds
                passes.append(current_pass)
            current_pass={}
    passes.sort(key=lambda p:p["aos"])
    return render_template("passes.html", passes=passes, message=warn, info=info, tle_last_updated=get_tle_last_updated(), show_local_time=show_local_time)

@app.route("/import-settings", methods=["GET","POST"])
def import_settings():
    msg=None
    if request.method=="POST":
        file=request.files.get("settings_file")
        if file and file.filename.endswith(".json"):
            try:
                data=json.load(file)
                with open(CONFIG_FILE,"w") as f: json.dump(data.get("config",{}),f,indent=4)
                msg="Settings imported successfully."
            except Exception as e: msg=f"Error importing settings: {e}"
        else: msg="Please upload a valid .json file."
    return render_template("import_settings.html", message=msg)

@app.route("/export-settings")
def export_settings():
    data={"config":{}}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: data["config"]=json.load(f)
    return app.response_class(json.dumps(data,indent=4), mimetype="application/json", headers={"Content-Disposition":"attachment;filename=settings.json"})

@app.route("/export-settings-page")
def export_settings_page(): return render_template("export_settings.html")

if __name__=="__main__": app.run(debug=True, host="0.0.0.0")
