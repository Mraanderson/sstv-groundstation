from flask import Flask, render_template, request, redirect, jsonify, send_from_directory
import os, json, requests

app = Flask(__name__)
ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(ROOT, "../images")
CONFIG_PATH = os.path.join(ROOT, "config.json")

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

@app.route("/config", methods=["GET", "POST"])
def config():
    cfg = load_config()
    sat_cfg = cfg["satellites"].get(cfg["selected_satellite"], {})
    images = sorted([f for f in os.listdir(IMG_DIR) if f.endswith(".png")], reverse=True)

    if request.method == "POST":
        cfg["location"]["lat"] = float(request.form.get("lat", 0))
        cfg["location"]["lon"] = float(request.form.get("lon", 0))
        cfg["location"]["elev_m"] = int(request.form.get("elev_m", 0))
        cfg["selected_satellite"] = request.form.get("satellite", cfg["selected_satellite"])
        cfg["sstv_mode"] = request.form.get("sstv_mode", "PD120")
        sat_name = cfg["selected_satellite"]
        cfg["satellites"][sat_name] = {
            "tle_group": request.form.get("tle_group", "stations"),
            "freq_hz": int(request.form.get("freq_hz", 145800000)),
            "nominal_mode": cfg["sstv_mode"]
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        return redirect("/config")

    return render_template("config.html", cfg=cfg, sat_cfg=sat_cfg, images=images[:8])

@app.route("/get-satellites")
def get_satellites():
    tle_group = request.args.get("group", "stations")
    url = f"https://celestrak.org/NORAD/elements/{tle_group}.txt"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        lines = r.text.strip().splitlines()
        names = [lines[i].strip() for i in range(0, len(lines), 3)]
        return jsonify(names)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/gallery")
def gallery():
    images = sorted([f for f in os.listdir(IMG_DIR) if f.endswith(".png")], reverse=True)
    return render_template("gallery.html", images=images)

@app.route("/images/<filename>")
def image(filename):
    return send_from_directory(IMG_DIR, filename)

@app.route("/")
def home():
    return redirect("/config")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
