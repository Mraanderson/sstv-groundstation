#!/bin/bash
set -e

# === Basic setup ===
APP_DIR="/opt/sstv-groundstation"
APP_USER="${SUDO_USER:-$USER}"

# === Install dependencies ===
sudo apt-get update
sudo apt-get install -y rtl-sdr ffmpeg python3-pip python3-venv at cron git
sudo pip3 install flask skyfield pytz

# === Create app structure ===
sudo mkdir -p "$APP_DIR"/{app/scripts,app/templates,app/static/images,images,logs}
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# === Python virtual environment ===
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"
pip install flask skyfield pytz

# === Config file ===
cat > "$APP_DIR/app/config.json" <<EOF
{
  "location": {
    "lat": 50.000,
    "lon": -2.000,
    "elev_m": 50
  },
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

# === Web app ===
cat > "$APP_DIR/app/app.py" <<EOF
from flask import Flask, render_template, request, redirect, send_from_directory
import os, json, subprocess

app = Flask(__name__)
ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(ROOT, "../images")
CONFIG_PATH = os.path.join(ROOT, "config.json")
UPCOMING_PATH = os.path.join(ROOT, "upcoming_passes.json")

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

@app.route("/")
def index():
    cfg = load_config()
    images = sorted([f for f in os.listdir(IMG_DIR) if f.endswith(".png")], reverse=True)
    return render_template("index.html", cfg=cfg, images=images[:8])

@app.route("/images/<filename>")
def image(filename):
    return send_from_directory(IMG_DIR, filename)

@app.route("/set-satellite", methods=["POST"])
def set_satellite():
    cfg = load_config()
    sel = request.form.get("satellite", "ISS")
    cfg["selected_satellite"] = sel
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    subprocess.Popen(["python3", os.path.join(ROOT, "scripts/pass_scheduler.py")])
    return redirect("/")

@app.route("/record-now", methods=["POST"])
def record_now():
    freq = request.form.get("freq_hz", "145800000")
    dur = request.form.get("duration_sec", "600")
    mode = request.form.get("mode", "PD120")
    sat = request.form.get("satellite", "MANUAL")
    aos = request.form.get("aos_utc", "")
    subprocess.Popen([
        os.path.join(ROOT, "scripts/record_sstv.sh"),
        freq, dur, mode, sat, aos
    ])
    return redirect("/")
EOF

# === Templates ===
mkdir -p "$APP_DIR/app/templates"
cat > "$APP_DIR/app/templates/index.html" <<EOF
<!doctype html>
<html>
<head><title>SSTV Ground Station</title></head>
<body>
<h1>SSTV Ground Station</h1>
<form action="/set-satellite" method="post">
  <label>Select Satellite:</label>
  <select name="satellite">
    <option value="ISS">ISS</option>
  </select>
  <input type="submit" value="Set">
</form>
<form action="/record-now" method="post">
  <input name="satellite" value="ISS">
  <input name="freq_hz" value="145800000">
  <input name="duration_sec" value="600">
  <input name="mode" value="PD120">
  <input type="submit" value="Record Now">
</form>
<h2>Latest Images</h2>
{% for img in images %}
  <div><img src="/images/{{ img }}" width="300"><br>{{ img }}</div>
{% endfor %}
</body>
</html>
EOF

# === Recording script ===
cat > "$APP_DIR/app/scripts/record_sstv.sh" <<EOF
#!/bin/bash
FREQ="\$1"
DUR="\$2"
MODE="\$3"
SAT="\$4"
AOS="\$5"
STAMP=\$(date -u +%Y%m%d_%H%M%S)
OUT="/opt/sstv-groundstation/images/\${SAT}_\${STAMP}.wav"
rtl_fm -f \$FREQ -M fm -s 22050 -r 22050 - | ffmpeg -i - -f wav "\$OUT"
if command -v rxsstv >/dev/null; then
  rxsstv -m \$MODE -i "\$OUT" -o "/opt/sstv-groundstation/images/\${SAT}_\${STAMP}.png"
fi
EOF
chmod +x "$APP_DIR/app/scripts/record_sstv.sh"

# === Pass scheduler ===
cat > "$APP_DIR/app/scripts/pass_scheduler.py" <<EOF
# Placeholder for pass prediction logic using Skyfield
# You can expand this later to schedule recordings via 'at'
print("Pass prediction not yet implemented.")
EOF

# === Start Flask app ===
cat > /etc/systemd/system/sstv-web.service <<EOF
[Unit]
Description=SSTV Ground Station Web UI
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR/app
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/app/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now sstv-web.service

echo "✅ SSTV Ground Station installed."
echo "🌐 Visit: http://$(hostname -I | awk '{print $1}'):5000"

