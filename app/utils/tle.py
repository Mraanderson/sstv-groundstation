import os
import requests

# Map satellite names to their NORAD catalog numbers
TLE_SOURCES = {
    "ISS": 25544,
    #"UMKA 1": 57172,
    # Add more satellites here if you want to track them
}

TLE_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "tle")

def fetch_tle(sat_name):
    """Fetch a TLE for the given satellite name from Celestrak GP API."""
    catnr = TLE_SOURCES.get(sat_name)
    if not catnr:
        print(f"⚠ No NORAD ID for {sat_name}")
        return None

    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={catnr}&FORMAT=TLE"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        lines = res.text.strip().splitlines()
        if len(lines) >= 3:
            return {"name": lines[0], "line1": lines[1], "line2": lines[2]}
        else:
            print(f"⚠ Incomplete TLE for {sat_name}")
            return None
    except Exception as e:
        print(f"❌ Failed to fetch TLE for {sat_name}: {e}")
        return None

def save_tle(tle_data):
    """Save a list of TLE dicts to active.txt in the TLE_DIR."""
    os.makedirs(TLE_DIR, exist_ok=True)
    path = os.path.join(TLE_DIR, "active.txt")
    try:
        with open(path, "w") as f:
            for tle in tle_data:
                f.write(f"{tle['name']}\n{tle['line1']}\n{tle['line2']}\n")
        print(f"✅ TLEs saved to {path}")
    except Exception as e:
        print(f"❌ Failed to save TLEs: {e}")
        
