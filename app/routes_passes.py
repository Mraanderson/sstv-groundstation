import json
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for
from skyfield.api import Loader, wgs84, EarthSatellite
from .utils import (
    CONFIG_FILE, TLE_FILE,
    config_exists_and_valid, tle_needs_refresh,
    fetch_latest_tle, get_tle_last_updated
)

bp = Blueprint('passes', __name__)

@bp.route("/passes")
def passes_page():
    if not config_exists_and_valid():
        return redirect(url_for('config.config_page'))

    if tle_needs_refresh():
        try:
            fetch_latest_tle()
        except Exception as e:
            return render_template(
                "passes.html",
                passes=[],
                message=f"TLE refresh failed: {e}",
                tle_last_updated=get_tle_last_updated()
            )

    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    lat, lon, alt = float(cfg.get("location_lat", 0)), float(cfg.get("location_lon", 0)), float(cfg.get("location_alt", 0))
    show_local_time = bool(cfg.get("show_local_time", True))

    with open(TLE_FILE) as f:
        name, l1, l2 = f.read().strip().splitlines()[:3]

    ts = Loader('./skyfield_data').timescale()
    observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)
    sat = EarthSatellite(l1, l2, name, ts)

    tle_epoch_dt = sat.epoch.utc_datetime().replace(tzinfo=timezone.utc)
    tle_age_days = (datetime.now(timezone.utc) - tle_epoch_dt).total_seconds() / 86400.0
    info = {
        "tle_epoch_utc": tle_epoch_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "tle_age_days": round(tle_age_days, 2),
        "observer": {"lat": lat, "lon": lon, "alt_m": alt},
        "min_elev_deg": 0.0
    }
    warn = "TLE is older than 7 days — refresh from CelesTrak." if tle_age_days > 7 else None

    # ✅ Make now_utc timezone-aware
    now_utc = datetime.now(timezone.utc)
    start, end = now_utc, now_utc + timedelta(hours=24)

    passes = []
    try:
        t, events = sat.find_events(
            observer,
            ts.from_datetime(start),
            ts.from_datetime(end),
            altitude_degrees=info["min_elev_deg"]
        )
    except Exception as e:
        return render_template(
            "passes.html",
            passes=[],
            message=f"Error finding passes: {e}",
            info=info,
            tle_last_updated=get_tle_last_updated(),
            show_local_time=show_local_time
        )

    current = {}
    for ti, ev in zip(t, events):
        if ev == 0:
            current = {
                "satellite": "ISS (ZARYA)",
                "aos": ti.utc_datetime().replace(tzinfo=timezone.utc)
            }
        elif ev == 1:
            current["max_elev"] = (sat - observer).at(ti).altaz()[0].degrees
        elif ev == 2:
            current["los"] = ti.utc_datetime().replace(tzinfo=timezone.utc)
            if "aos" in current and "los" in current:
                current["duration"] = (current["los"] - current["aos"]).seconds
                if current["aos"] <= now_utc <= current["los"]:
                    current["row_class"] = "table-warning"
                elif current["aos"] <= now_utc + timedelta(hours=1) and current["aos"] > now_utc:
                    current["row_class"] = "table-info"
                else:
                    current["row_class"] = ""
                passes.append(current)
            current = {}

    passes.sort(key=lambda p: p["aos"])
    return render_template(
        "passes.html",
        passes=passes,
        message=warn,
        info=info,
        tle_last_updated=get_tle_last_updated(),
        show_local_time=show_local_time
    )
    
