from flask import Flask, render_template, send_from_directory, request, redirect, url_for
import os, json, time
# If you want optional downloading, uncomment:
# import requests

app = Flask(__name__)

# Existing constants...
IMAGES_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'images'))
CONFIG_FILE = os.path.join(app.root_path, 'config.json')

# New: TLE directory (root-level tle/)
TLE_DIR = os.path.abspath(os.path.join(app.root_path, '..', 'tle'))
os.makedirs(TLE_DIR, exist_ok=True)

# Define the allowed TLE sources here.
# You can expand this dictionary as you add sources.
# filename must be .txt and unique per satellite.
TLE_SOURCES = {
    "iss": {
        "label": "ISS (Zarya)",
        "filename": "iss.txt",
        # "url": "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE"  # optional
    },
    "noaa-19": {
        "label": "NOAA-19",
        "filename": "noaa19.txt",
        # "url": "https://celestrak.org/NORAD/elements/noaa.txt"
    },
    "metop-b": {
        "label": "MetOp-B",
        "filename": "metopb.txt",
        # "url": "https://celestrak.org/NORAD/elements/metop.txt"
    },
    # Add more sources as needed...
}

def tle_file_path(filename: str) -> str:
    # Restrict to TLE_DIR and .txt only
    safe = os.path.basename(filename)
    if not safe.endswith(".txt"):
        raise ValueError("Invalid TLE filename")
    return os.path.join(TLE_DIR, safe)

def list_enabled_sources():
    """Return set of keys from TLE_SOURCES that currently have a file present."""
    enabled = set()
    for key, src in TLE_SOURCES.items():
        fpath = tle_file_path(src["filename"])
        if os.path.exists(fpath):
            enabled.add(key)
    return enabled

def source_last_updated(key: str) -> str:
    src = TLE_SOURCES[key]
    fpath = tle_file_path(src["filename"])
    if os.path.exists(fpath):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(fpath)))
    return "N/A"

def write_placeholder_tle(fpath: str, label: str):
    """Create a minimal placeholder TLE file. Replace with real content as needed."""
    content = f"# {label}\n# Placeholder TLE — replace with fetch task\n"
    with open(fpath, "w") as f:
        f.write(content)

# Optional: enable this to download TLE content when selecting a source
# def fetch_and_write_tle(url: str, fpath: str):
#     r = requests.get(url, timeout=10)
#     r.raise_for_status()
#     with open(fpath, "w") as f:
#         f.write(r.text.strip() + "\n")

@app.route("/tle/manage", methods=["GET", "POST"])
def tle_manage():
    message = None
    if request.method == "POST":
        # Determine which sources were selected
        selected = set(request.form.getlist("enabled"))  # list of keys
        allowed_keys = set(TLE_SOURCES.keys())

        # Sanity check: ignore unknown keys
        selected = selected.intersection(allowed_keys)

        # Enable newly selected: create/update files
        for key in selected:
            src = TLE_SOURCES[key]
            fpath = tle_file_path(src["filename"])
            # If you want to download real data (when url present), use fetch:
            # if "url" in src:
            #     fetch_and_write_tle(src["url"], fpath)
            # else:
            #     write_placeholder_tle(fpath, src["label"])
            write_placeholder_tle(fpath, src["label"])

        # Disable deselected: remove files that are no longer selected
        currently_enabled = list_enabled_sources()
        for key in (currently_enabled - selected):
            src = TLE_SOURCES[key]
            fpath = tle_file_path(src["filename"])
            try:
                os.remove(fpath)
            except FileNotFoundError:
                pass

        message = "TLE selections saved."

    enabled = list_enabled_sources()

    # Attach last_updated field to display for enabled entries
    sources_view = {}
    for key, src in TLE_SOURCES.items():
        sources_view[key] = dict(src)
        sources_view[key]["last_updated"] = source_last_updated(key)

    return render_template("tle_manage.html", sources=sources_view, enabled=enabled, message=message)
    
