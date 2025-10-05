import os
from pathlib import Path
import time
import json

RECORDINGS_DIR = Path("recordings")
STATE_FILE = os.path.expanduser("~/sstv-groundstation/current_pass.json")


def is_pass_in_progress():
    if not os.path.exists(STATE_FILE):
        return False
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        # Optionally, check end_time
        return True
    except Exception:
        return False


def cleanup_orphan_iq():
    """Delete all orphan IQ files (not in use by a current pass)."""
    in_progress = is_pass_in_progress()
    deleted = []
    for f in RECORDINGS_DIR.glob("*.iq"):
        if in_progress:
            # If pass in progress, skip deleting the current IQ file
            try:
                with open(STATE_FILE) as state:
                    state_data = json.load(state)
                if str(f) == state_data.get("iq_file"):
                    continue
            except Exception:
                pass
        try:
            os.remove(f)
            deleted.append(str(f))
        except Exception:
            pass
    return deleted


def periodic_cleanup(interval_minutes=30):
    """Run orphan IQ cleanup every interval_minutes, avoiding the half hour and pass times."""
    while True:
        now = time.localtime()
        # Avoid running at :00 or :30 (half hour)
        if now.tm_min not in (0, 30):
            cleanup_orphan_iq()
        time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    cleanup_orphan_iq()
