import os, json, requests
from datetime import datetime, timezone
from timezonefinder import TimezoneFinder

IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'images'))
TLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tle'))
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
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
        return all(cfg.get(k) for k in ["location_lat","location_lon","location_alt","timezone"])
    except: return False

def get_tle_last_updated():
    if os.path.exists(TLE_FILE):
        m = datetime.fromtimestamp(os.path.getmtime(TLE_FILE), tz=timezone.utc)
        return m.strftime("%Y-%m-%d %H:%M:%S UTC")
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
    m = datetime.fromtimestamp(os.path.getmtime(TLE_FILE), tz=timezone.utc)
    return (datetime.now(timezone.utc)-m).total_seconds()/86400.0 > max_age_days

def get_timezone_for_coords(lat, lon):
    tf = TimezoneFinder()
    return tf.timezone_at(lat=lat, lng=lon) or tf.closest_timezone_at(lat=lat, lng=lon) or ""
    
