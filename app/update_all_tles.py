import requests
import os

# Root-level tle/ folder
TLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tle'))
os.makedirs(TLE_DIR, exist_ok=True)

# Define your satellites and their CelesTrak URLs
TLE_SOURCES = {
    "iss.txt": "https://celestrak.org/NORAD/elements/stations.txt",   # ISS (ZARYA)
    "noaa19.txt": "https://celestrak.org/NORAD/elements/noaa.txt",    # NOAA-19
    "metopb.txt": "https://celestrak.org/NORAD/elements/metop.txt",   # MetOp-B
    # Add more here as needed
}

def fetch_tle(url, sat_name=None):
    """Fetch TLE from URL. If sat_name is given, extract only that satellite's block."""
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
    for filename, url in TLE_SOURCES.items():
        # If the URL contains multiple satellites, you can filter by name here:
        # content = fetch_tle(url, "ISS (ZARYA)")
        content = fetch_tle(url)
        file_path = os.path.join(TLE_DIR, filename)
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Updated {file_path}")

if __name__ == "__main__":
    try:
        update_all()
        print("All TLEs updated successfully.")
    except Exception as e:
        print(f"Error updating TLEs: {e}")
      
