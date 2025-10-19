# File: sstv-groundstation/update_tles.py

import os
import logging
import requests

# --- Configuration (Corrected for new location) ---
# Get the directory of the current script (e.g., /path/to/sstv-groundstation/app/utils)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Navigate up two levels to get the project's root directory
APP_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# The URL for CelesTrak's complete, consolidated list of active satellite TLEs.
TLE_SOURCE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"

# The destination file, now correctly built from the project root.
TLE_DEST_FILE = os.path.join(APP_DIR, "app", "static", "tle", "active.txt")

# Network request timeout in seconds.
REQUEST_TIMEOUT = 60

# --- Logging Setup ---
# This will output clean, timestamped logs, perfect for systemd/journalctl.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [TLE_Updater] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def run_tle_update():
    """
    Fetches a consolidated TLE file for all active satellites and saves it.
    This single function performs the entire task.
    """
    logging.info(f"Starting TLE update task. Source: {TLE_SOURCE_URL}")

    try:
        # 1. Fetch the consolidated TLE data in a single request.
        response = requests.get(TLE_SOURCE_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        new_tle_data = response.text

        # 2. Ensure the destination directory exists.
        os.makedirs(os.path.dirname(TLE_DEST_FILE), exist_ok=True)

        # 3. Check if the content has changed to avoid unnecessary disk writes.
        if os.path.exists(TLE_DEST_FILE):
            try:
                with open(TLE_DEST_FILE, "r") as f:
                    if f.read() == new_tle_data:
                        logging.info("TLE data is already up-to-date. No changes made.")
                        return
            except IOError:
                logging.warning("Could not read existing TLE file. Overwriting.")

        # 4. Write the new data to the destination file.
        with open(TLE_DEST_FILE, "w") as f:
            f.write(new_tle_data)

        logging.info(f"Successfully updated and saved TLE data to {TLE_DEST_FILE}")

    except requests.exceptions.RequestException as e:
        logging.error(f"A network error occurred while fetching TLE data: {e}")
    except IOError as e:
        logging.error(f"A file I/O error occurred while saving TLE data: {e}")
    except Exception as e:
        logging.critical(f"An unexpected critical error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    # This block makes the script executable from the command line.
    # When systemd runs `python3 update_tles.py`, this is the code that will execute.
    run_tle_update()
