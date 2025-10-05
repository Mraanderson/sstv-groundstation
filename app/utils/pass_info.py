from skyfield.api import Loader, EarthSatellite, wgs84
from datetime import datetime
from zoneinfo import ZoneInfo
import os

TLE_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "tle", "active.txt")


def get_iss_info_at(dt: datetime, lat: float, lon: float, alt: float, tz: str = "UTC"):
    """
    Return ISS position (lat, lon), altitude (km), and max elevation at a given datetime.
    """
    if not os.path.exists(TLE_PATH):
        return None
    load = Loader("./skyfield_data")
    ts = load.timescale()
    observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)
    with open(TLE_PATH) as f:
        lines = [line.strip() for line in f if line.strip()]
    for i in range(0, len(lines), 3):
        name, l1, l2 = lines[i], lines[i+1], lines[i+2]
        if "ISS" not in name.upper():
            continue
        sat = EarthSatellite(l1, l2, name, ts)
        t = ts.from_datetime(dt)
        geo = sat.at(t).subpoint()
        alt_km = geo.elevation.km
        iss_lat = geo.latitude.degrees
        iss_lon = geo.longitude.degrees
        # Max elevation: compute for observer
        difference = sat - observer
        alt_deg = difference.at(t).altaz()[0].degrees
        return {
            "iss_lat": iss_lat,
            "iss_lon": iss_lon,
            "iss_alt_km": alt_km,
            "iss_elev_deg": alt_deg
        }
    return None
