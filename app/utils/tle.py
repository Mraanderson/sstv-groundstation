import os, requests, tempfile, shutil

# Map satellite names to their NORAD catalog numbers
TLE_SOURCES = {
    "ISS": 25544,
    # "UMKA 1": 57172,
}

TLE_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "tle")
ACTIVE_PATH = os.path.join(TLE_DIR, "active.txt")

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

def save_tles(tle_list, append=False):
    """Save TLEs to active.txt. Only writes if we have valid data."""
    if not tle_list:
        print("⚠ No new TLEs fetched, keeping existing file")
        return

    os.makedirs(TLE_DIR, exist_ok=True)
    mode = "a" if append else "w"

    # Write to a temp file first if overwriting
    if not append:
        fd, tmp = tempfile.mkstemp(dir=TLE_DIR)
        with os.fdopen(fd, "w") as f:
            for tle in tle_list:
                f.write(f"{tle['name']}\n{tle['line1']}\n{tle['line2']}\n")
        shutil.move(tmp, ACTIVE_PATH)
    else:
        with open(ACTIVE_PATH, mode) as f:
            for tle in tle_list:
                f.write(f"{tle['name']}\n{tle['line1']}\n{tle['line2']}\n")

    print(f"✅ TLEs saved to {ACTIVE_PATH}")

def update_tles():
    """Fetch all satellites and update active.txt only if successful."""
    new_tles = []
    for name in TLE_SOURCES:
        tle = fetch_tle(name)
        if tle:
            new_tles.append(tle)

    save_tles(new_tles, append=False)  # set append=True if you want to add to existing