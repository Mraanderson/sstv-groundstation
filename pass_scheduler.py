import json
import os
from datetime import datetime, timedelta
from skyfield.api import load, Topos
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "../config.json")
RECORD_SCRIPT = os.path.join(ROOT, "record_sstv.sh")

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def schedule_recording(pass_time, freq, duration, mode, sat_name):
    timestamp = pass_time.strftime("%H:%M %d.%m.%Y")
    cmd = f'echo "{RECORD_SCRIPT} {freq} {duration} {mode} {sat_name} {pass_time.isoformat()}" | at -M {timestamp}'
    subprocess.run(cmd, shell=True)
    print(f"📅 Scheduled: {sat_name} at {timestamp} UTC")

def main():
    cfg = load_config()
    location = cfg["location"]
    sat_name = cfg["selected_satellite"]
    sat_cfg = cfg["satellites"][sat_name]
    min_elev = cfg["elevation_min_deg"]
    horizon = cfg["prediction_horizon_hours"]
    duration = cfg["record_margin_sec"] * 2  # rough estimate

    ts = load.timescale()
    now = datetime.utcnow()
    end = now + timedelta(hours=horizon)

    eph = load('de421.bsp')
    sats = load.tle_file('https://celestrak.org/NORAD/elements/stations.txt')
    satellite = next(s for s in sats if s.name == sat_name)

    observer = Topos(latitude_degrees=location["lat"],
                     longitude_degrees=location["lon"],
                     elevation_m=location["elev_m"])

    times = ts.utc(now.year, now.month, now.day, range(now.hour, end.hour + 1))
    for t in times:
        alt, az, _ = satellite.at(t).observe(observer).apparent().altaz()
        if alt.degrees > min_elev:
            pass_time = t.utc_datetime()
            schedule_recording(pass_time, sat_cfg["freq_hz"], duration, sat_cfg["nominal_mode"], sat_name)

if __name__ == "__main__":
    main()
  
