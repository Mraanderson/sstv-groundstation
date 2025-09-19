import os
import csv
import requests
from datetime import datetime, timedelta, timezone
from flask import render_template, current_app, jsonify
from skyfield.api import Loader, EarthSatellite, wgs84
from zoneinfo import ZoneInfo

from . import bp
from app.utils.sdr import rtl_sdr_present  # RTL-SDR detection helper

# Single reliable satellite for testing
SSTV_SATELLITES = [
    {
        "name": "ISS (ZARYA)",
        "norad_id": 25544,
        "frequency": "145.800",
        "status": "Active",
        "notes": "ARISS SSTV events"
    }
]

def tle_file_path():
    return os.path.join(current_app.config["TLE_DIR"], "active.txt")

def load_tle_satellites():
    """Load satellites from the TLE file."""
    tle_path = tle_file_path()
    if not os.path.exists(tle_path):
        return None, []
    with open(tle_path) as f:
        lines = [line.strip() for line in f if line.strip()]
    satellites = [lines[i] for i in range(0, len(lines), 3)]
    return tle_path, satellites

def get_tle_age_days(tle_path):
    try:
        with open(tle_path) as f:
            lines = [line.strip() for line in f if line.strip()]
        if len(lines) < 2:
            return None
        line1 = lines[1]
        epoch_str = line1[18:32]  # YYDDD.DDDDDDDD
        year = int(epoch_str[:2])
        year += 2000 if year < 57 else 1900
        day_of_year = float(epoch_str[2:])
        epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)
        return round((datetime.now(timezone.utc) - epoch).total_seconds() / 86400, 1)
    except Exception:
        return None

@bp.route("/", endpoint="passes_page")
def passes_page():
    lat = current_app.config.get("LATITUDE")
    lon = current_app.config.get("LONGITUDE")
    alt = current_app.config.get("ALTITUDE_M")
    tz = current_app.config.get("TIMEZONE")

    tle_path, satellites = load_tle_satellites()
    tle_info = None
    passes = []
    sdr_flag = rtl_sdr_present()  # detect SDR once per request

    if tle_path:
        mtime = datetime.fromtimestamp(os.path.getmtime(tle_path))
        tle_info = {
            "filename": os.path.basename(tle_path),
            "last_updated": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            "age_days": get_tle_age_days(tle_path)
        }

        if None not in (lat, lon, alt, tz):
            load = Loader("./skyfield_data")
            ts = load.timescale()
            observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)

            with open(tle_path) as f:
                lines = [line.strip() for line in f if line.strip()]

            now_utc = datetime.now(timezone.utc)
            end_utc = now_utc + timedelta(hours=24)
            t0 = ts.from_datetime(now_utc)
            t1 = ts.from_datetime(end_utc)

            for i in range(0, len(lines), 3):
                try:
                    name, l1, l2 = lines[i], lines[i+1], lines[i+2]
                except IndexError:
                    continue

                try:
                    sat = EarthSatellite(l1, l2, name, ts)
                except Exception as e:
                    print(f"Failed to build satellite for {name}: {e}")
                    continue

                try:
                    times, events = sat.find_events(observer, t0, t1, altitude_degrees=0.0)
                except Exception as e:
                    print(f"find_events failed for {name}: {e}")
                    continue

                # Group into passes: rise (0), culminate (1), set (2)
                for j in range(0, len(events) - 2, 3):
                    if events[j] == 0 and events[j+1] == 1 and events[j+2] == 2:
                        start = times[j].utc_datetime().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(tz))
                        peak = times[j+1].utc_datetime().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(tz))
                        end = times[j+2].utc_datetime().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(tz))
                        # Correct max elevation calculation
                        peak_time = ts.from_datetime(times[j+1].utc_datetime())
                        alt_deg = observer.observe(sat).at(peak_time).apparent().altaz()[0].degrees
                        passes.append({
                            "satellite": name,
                            "start": start,
                            "peak": peak,
                            "end": end,
                            "max_elevation": round(alt_deg, 1)
                        })

            passes.sort(key=lambda p: p["start"])

            # Log any passes that have already ended
            log_path = os.path.join(current_app.config["TLE_DIR"], "pass_log.csv")
            try:
                with open(log_path, "a", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    for p in passes:
                        if p["end"] < datetime.now(ZoneInfo(tz)):
                            writer.writerow([
                                datetime.now().isoformat(),  # log timestamp
                                p["satellite"],
                                p["start"].isoformat(),
                                p["peak"].isoformat(),
                                p["end"].isoformat(),
                                p["max_elevation"],
                                sdr_flag,
                                ""  # placeholder for quality
                            ])
            except Exception as e:
                print(f"Pass logging failed: {e}")

    now_for_template = None
    if tz:
        try:
            now_for_template = datetime.now(ZoneInfo(tz))
        except Exception:
            now_for_template = datetime.now()

    return render_template(
        "passes/passes.html",
        tle_info=tle_info,
        satellites=satellites,
        passes=passes,
        timezone=tz,
        now=now_for_template,
        location_set=None not in (lat, lon, alt, tz),
        sstv_sats=SSTV_SATELLITES,
        sdr_present=sdr_flag
    )

@bp.route("/update-tle", endpoint="update_tle")
def update_tle():
    try:
        tle_dir = current_app.config["TLE_DIR"]
        os.makedirs(tle_dir, exist_ok=True)
        path = tle_file_path()

        iss = SSTV_SATELLITES[0]
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={iss['norad_id']}&FORMAT=TLE"
        print(f"Fetching TLE for {iss['name']} from {url}")
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        tle_lines = resp.text.strip().splitlines()

        if len(tle_lines) < 3:
            print(f"Warning: TLE for {iss['name']} is incomplete")
            return jsonify({"status": "error", "message": "Incomplete TLE"})

        with open(path, "w") as f:
            f.write("\n".join(tle_lines[:3]) + "\n")

        print(f"TLE saved successfully to {path}")
        return jsonify({"status": "success", "updated": True})
    except Exception as e:
        print("TLE update failed:", e)
        return jsonify({"status": "error", "message": str(e)})
        
