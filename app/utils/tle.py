import os
import time
import requests

def fetch_latest_tle(tle_dir, tle_url="https://celestrak.org/NORAD/elements/stations.txt"):
    """
    Download the latest TLE data from the given URL and save it to tle_dir.
    """
    os.makedirs(tle_dir, exist_ok=True)
    tle_path = os.path.join(tle_dir, "stations.txt")
    response = requests.get(tle_url, timeout=10)
    response.raise_for_status()
    with open(tle_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    return tle_path

def tle_needs_refresh(tle_dir, max_age_hours=12):
    """
    Check if the TLE file is older than max_age_hours.
    Returns True if it needs refreshing.
    """
    tle_path = os.path.join(tle_dir, "stations.txt")
    if not os.path.exists(tle_path):
        return True
    age_hours = (time.time() - os.path.getmtime(tle_path)) / 3600
    return age_hours > max_age_hours

def get_tle_last_updated(tle_dir):
    """
    Return the last modified time of the TLE file as a timestamp.
    Returns None if the file doesn't exist.
    """
    tle_path = os.path.join(tle_dir, "stations.txt")
    if not os.path.exists(tle_path):
        return None
    return os.path.getmtime(tle_path)
  
