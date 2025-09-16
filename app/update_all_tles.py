import requests
import os
import json

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TLE_DIR = os.path.join(BASE_DIR, 'tle')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'satellites.json')

os.makedirs(TLE_DIR, exist_ok=True)

def load_satellite_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def fetch_tle(url, sat_name=None):
    """
    Fetches TLE data from a URL.
    If sat_name is provided, extracts only that satellite's 3-line TLE.
    """
    print(f"Fetching from {url} ...")
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    lines = r.text.strip().splitlines()

    if sat_name:
        for i, line in enumerate(lines):
            if line.strip().upper().startswith(sat_name.upper()):
                return "\n".join(lines[i:i+3]) + "\n"
        raise ValueError(f"Satellite '{sat_name}' not found in {url}")
    else:
        return "\n".join(lines) + "\n"

def update_all():
    satellites = load_satellite_config()
    for name, info in satellites.items():
        if not info.get("enabled"):
            continue
        try:
            # If the TLE source is a multi-satellite file, filter by name
            content = fetch_tle(info["tle_url"], name if info["tle_url"].endswith("amateur.txt") or info["tle_url"].endswith("stations.txt") else None)
            file_path = os.path.join(TLE_DIR, info["filename"])
            with open(file_path, "w") as f:
                f.write(content)
            print(f"Updated {file_path}")
        except Exception as e:
            print(f"Error updating {name}: {e}")

if __name__ == "__main__":
    try:
        update_all()
        print("All enabled satellites updated successfully.")
    except Exception as e:
        print(f"Error updating TLEs: {e}")
        
