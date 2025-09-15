import requests
import os

# URL for ISS (ZARYA) TLE from CelesTrak
TLE_URL = "https://celestrak.org/NORAD/elements/stations.txt"

# Path to your root-level tle/ folder
TLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tle'))
os.makedirs(TLE_DIR, exist_ok=True)

# Output file
TLE_FILE = os.path.join(TLE_DIR, "iss.txt")

def update_iss_tle():
    try:
        print(f"Fetching ISS TLE from {TLE_URL} ...")
        response = requests.get(TLE_URL, timeout=10)
        response.raise_for_status()

        # The stations.txt file contains multiple entries; we only want ISS
        lines = response.text.strip().splitlines()
        iss_lines = []
        for i, line in enumerate(lines):
            if line.strip().upper().startswith("ISS"):
                iss_lines = lines[i:i+3]  # Name + 2 TLE lines
                break

        if not iss_lines:
            raise ValueError("ISS TLE not found in fetched data.")

        with open(TLE_FILE, "w") as f:
            f.write("\n".join(iss_lines) + "\n")

        print(f"ISS TLE updated: {TLE_FILE}")
    except Exception as e:
        print(f"Error updating ISS TLE: {e}")

if __name__ == "__main__":
    update_iss_tle()
  
