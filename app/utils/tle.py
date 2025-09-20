import requests
from datetime import datetime
from pathlib import Path

TLE_SOURCES = {
    "ISS": "https://celestrak.org/NORAD/elements/stations.txt",
    "UMKA-1": "https://celestrak.org/NORAD/elements/active.txt"
}

TLE_CACHE = Path("app/static/tle_cache.txt")

def fetch_tle(satellite_name):
    url = TLE_SOURCES.get(satellite_name)
    if not url:
        raise ValueError(f"No TLE source for {satellite_name}")

    res = requests.get(url)
    res.raise_for_status()

    lines = res.text.strip().splitlines()
    for i in range(0, len(lines), 3):
        name = lines[i].strip()
        if name.upper() == satellite_name.upper():
            return {
                "name": name,
                "line1": lines[i + 1].strip(),
                "line2": lines[i + 2].strip()
            }
    return None

def save_tle(tle_data):
    with open(TLE_CACHE, "w") as f:
        for sat in tle_data:
            f.write(f"{sat['name']}\n{sat['line1']}\n{sat['line2']}\n")

def load_tle():
    if not TLE_CACHE.exists():
        return []

    with open(TLE_CACHE) as f:
        lines = f.read().strip().splitlines()

    tle_list = []
    for i in range(0, len(lines), 3):
        tle_list.append({
            "name": lines[i],
            "line1": lines[i + 1],
            "line2": lines[i + 2]
        })
    return tle_list

def get_tle_age_days(line1):
    try:
        epoch_str = line1[18:32]  # YYDDD.DDDDDDDD
        year = int(epoch_str[:2])
        year += 2000 if year < 57 else 1900
        day_of_year = float(epoch_str[2:])
        epoch = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
        return (datetime.utcnow() - epoch).total_seconds() / 86400
    except Exception:
        return None
        
