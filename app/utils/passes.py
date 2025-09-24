from skyfield.api import Loader, EarthSatellite, wgs84
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import csv
from pathlib import Path

PASS_FILE = Path("predicted_passes.csv")

def save_predicted_passes(passes):
    with PASS_FILE.open("w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["satellite", "aos", "los", "max_elev"])
        for p in passes:
            writer.writerow([
                p["satellite"],
                p["start"].astimezone(ZoneInfo("UTC")).isoformat(timespec="seconds"),
                p["end"].astimezone(ZoneInfo("UTC")).isoformat(timespec="seconds"),
                p["max_elevation"]
            ])

def generate_predictions(lat, lon, alt, tz, tle_path):
    """Generate passes for next 24h and save to predicted_passes.csv"""
    passes = []
    if None in (lat, lon, alt, tz) or not tle_path:
        return passes

    load = Loader("./skyfield_data")
    ts = load.timescale()
    observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)

    with open(tle_path) as f:
        lines = [line.strip() for line in f if line.strip()]

    now_utc = datetime.now(timezone.utc)
    end_utc = now_utc + timedelta(hours=24)
    t0, t1 = ts.from_datetime(now_utc), ts.from_datetime(end_utc)

    for i in range(0, len(lines), 3):
        try:
            name, l1, l2 = lines[i], lines[i+1], lines[i+2]
            sat = EarthSatellite(l1, l2, name, ts)
            times, events = sat.find_events(observer, t0, t1, altitude_degrees=0.0)
        except Exception:
            continue

        for j in range(0, len(events) - 2, 3):
            if events[j:j+3] == [0,1,2]:
                start = times[j].utc_datetime().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(tz))
                end   = times[j+2].utc_datetime().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(tz))
                peak_time = ts.from_datetime(times[j+1].utc_datetime())
                alt_deg = (sat - observer).at(peak_time).altaz()[0].degrees
                passes.append({
                    "satellite": name,
                    "start": start,
                    "end": end,
                    "max_elevation": round(alt_deg, 1)
                })

    passes.sort(key=lambda p: p["start"])
    save_predicted_passes(passes)
    return passes
