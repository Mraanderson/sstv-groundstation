sudo mkdir -p /opt/sstv-groundstation/{app/templates,app/static/images,images,logs} && sudo chown -R $USER:$USER /opt/sstv-groundstation && cd /opt/sstv-groundstation && python3 -m venv venv && source venv/bin/activate && pip install flask skyfield pytz && cat > app/config.json <<'EOF'
{
  "location": { "lat": 50.0, "lon": -2.0, "elev_m": 50 },
  "selected_satellite": "ISS",
  "sstv_mode": "PD120",
  "satellites": {
    "ISS": {
      "tle_group": "stations",
      "freq_hz": 145800000,
      "nominal_mode": "PD120"
    }
  },
  "elevation_min_deg": 10,
  "prediction_horizon_hours": 12,
  "record_margin_sec": 20
}
EOF
&& cat > app/app.py <<'EOF'
from flask import Flask, render_template, request, redirect
import os, json
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
        cfg["selected_satellite"] = request.form.get("satellite", "ISS")
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
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
EOF
&& cat > app/templates/config.html <<'EOF'
<!doctype html>
<html>
<head>
  <title>SSTV Ground Station Config</title>
  <style>
    body { font-family: sans-serif; margin: 2em; background: #f4f4f4; }
    h1, h2 { color: #333; }
    form { background: #fff; padding: 1em; border-radius: 8px; box-shadow: 0 0 10px #ccc; }
    label { display: block; margin-top: 1em; }
    input, select { width: 100%; padding: 0.5em; margin-top: 0.3em; }
    .gallery { margin-top: 2em; }
    .img-box { display: inline-block; margin: 1em; text-align: center; }
    .img-box img { width: 300px; border: 1px solid #ccc; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>SSTV Ground Station Configuration</h1>
  <form method="post">
    <label>Latitude:
      <input type="text" name="lat" value="{{ cfg.location.lat }}">
    </label>
    <label>Longitude:
      <input type="text" name="lon" value="{{ cfg.location.lon }}">
    </label>
    <label>Elevation (m):
      <input type="text" name="elev_m" value="{{ cfg.location.elev_m }}">
    </label>
    <label>Satellite:
      <select name="satellite">
        <option value="{{ cfg.selected_satellite }}">{{ cfg.selected_satellite }}</option>
      </select>
    </label>
    <label>TLE Group:
      <input type="text" name="tle_group" value="{{ sat_cfg.tle_group }}">
    </label>
    <label>Frequency (Hz):
      <input type="text" name="freq_hz" value="{{ sat_cfg.freq_hz }}">
    </label>
    <label>SSTV Mode:
      <input type="text" name="sstv_mode" value="{{ cfg.sstv_mode }}">
    </label>
    <input type="submit" value="Save Configuration">
  </form>
  <div class="gallery">
    <h2>Recent SSTV Captures</h2>
    {% for img in images %}
      <div class="img-box">
        <img src="/images/{{ img }}">
        <div>{{ img }}</div>
      </div>
    {% endfor %}
  </div>
</body>
</html>
EOF
