import requests
import os
import json
import re

# Sources to scan
SOURCES = {
    "stations": "https://celestrak.org/NORAD/elements/stations.txt",
    "amateur": "https://celestrak.org/NORAD/elements/amateur.txt"
}

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "satellites.json")

def fetch_satellite_names(url):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    lines = r.text.strip().splitlines()
    # Every TLE is 3 lines: name, line1, line2
    names = [lines[i].strip() for i in range(0, len(lines), 3)]
    return names

def safe_filename(name):
    return re.sub(r'[^A-Za-z0-9_\-]', '_', name.lower()) + ".txt"

def generate_satellites_json():
    satellites = {}
    for source_name, url in SOURCES.items():
        names = fetch_satellite_names(url)
        for name in names:
            satellites[name] = {
                "display_name": name,  # could be prettified later
                "enabled": False,
                "tle_url": url,
                "filename": safe_filename(name)
            }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(satellites, f, indent=4)
    print(f"Generated {OUTPUT_FILE} with {len(satellites)} satellites.")

if __name__ == "__main__":
    generate_satellites_json()
  
