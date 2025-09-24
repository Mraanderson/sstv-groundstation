import csv
import datetime
import time
import subprocess
import json
import sys
import threading
import select
import psutil
import schedule
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from app.utils import sdr
import app.utils.tle as tle_utils
import app.utils.passes as passes_utils
from app import config_paths

# --- CONFIG ---
SAT_FREQ = {"ISS": 145.800e6, "NOAA-19": 137.100e6}
RECORDINGS_DIR = Path("recordings")
LOG_DIR = Path("logs")
SETTINGS_FILE = Path("settings.json")
PASS_FILE = Path("predicted_passes.csv")
SAMPLE_RATE = 48000
GAIN = 27.9
ELEVATION_THRESHOLD = 0
START_EARLY = 30
STOP_LATE = 30
GREEN, RED, RESET = "\033[92m", "\033[91m", "\033[0m"

RECORDINGS_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("sstv_scheduler")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_DIR / "scheduler.log", maxBytes=1_000_000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)


def load_config_data():
    config_file = Path(config_paths.CONFIG_FILE)
    if config_file.exists():
        with open(config_file) as f:
            return json.load(f)
    return {}


def log_and_print(level, msg, plog=None):
    # Print inline updates for countdowns
    print(msg if "Next job" not in msg else f"\r{msg}", end="", flush=True)
    getattr(logger, level)(msg)
    if plog:
        getattr(plog, level)(msg)


def recordings_enabled():
    try:
        return SETTINGS_FILE.exists() and json.load(SETTINGS_FILE.open()).get("recording_enabled", False)
    except Exception:
        return False


def write_metadata(start_str, sat, aos, los, freq_hz, dur, size, verdict, error):
    meta = {
        "satellite": sat,
        "timestamp": aos.isoformat(),
        "aos": aos.isoformat(),
        "los": los.isoformat(),
        "frequency": round(freq_hz / 1e6, 3),
        "mode": "FM",
        "duration_s": dur,
        "file_mb": round(size, 2),
        "verdict": verdict,
        "sstv_detected": False,
        "callsigns": [],
        "error": error or None,
    }
    (RECORDINGS_DIR / f"{start_str}_{sat}.json").write_text(json.dumps(meta, indent=2))


def record_pass(sat, aos, los):
    start_str = aos.strftime("%Y%m%d_%H%M")
    wav_path = RECORDINGS_DIR / f"{start_str}_{sat}.wav"

    plog = logging.getLogger(start_str)
    plog.setLevel(logging.INFO)
    plog.addHandler(RotatingFileHandler(RECORDINGS_DIR / f"{start_str}_{sat}.log", maxBytes=200_000, backupCount=1))

    if not sdr.sdr_exists():
        return log_and_print("warning", f"[{sat}] SDR not detected — skipping.", plog)

    freq_lookup_key = sat.split()[0]
    freq = SAT_FREQ.get(freq_lookup_key)
    if not freq:
        return log_and_print("warning", f"[{sat}] No frequency configured — skipping.", plog)

    dur = int((los - aos).total_seconds()) + STOP_LATE
    log_and_print("info", f"[{sat}] ▶ Recording for {dur}s at {freq/1e6:.3f} MHz...", plog)

    error = None
    fm = None
    sox = None
    try:
        fm = subprocess.Popen(
            ["rtl_fm", "-f", str(int(freq)), "-M", "fm", "-s", str(SAMPLE_RATE), "-g", str(GAIN)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        sox = subprocess.Popen(
            ["sox", "-t", "raw", "-r", str(SAMPLE_RATE), "-e", "signed", "-b", "16", "-c", "1", "-", str(wav_path)],
            stdin=fm.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(dur)
    except Exception as e:
        error = str(e)
    finally:
        for p in (sox, fm):
            try:
                if p:
                    p.terminate()
            except Exception:
                pass

        size = wav_path.stat().st_size / (1024 * 1024) if wav_path.exists() else 0.0
        verdict = "PASS" if not error and size > 0 else "FAIL"
        print(f"{GREEN if verdict=='PASS' else RED}[{sat}] PASS COMPLETE — Verdict: {verdict} — File: {size:.2f} MB{RESET}")
        write_metadata(start_str, sat, aos, los, freq, dur, size, verdict, error)


def load_pass_predictions(path):
    if not Path(path).exists():
        return []
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    results = []
    for r in rows:
        try:
            sat = r["satellite"]
            aos = datetime.datetime.fromisoformat(r["aos"])
            los = datetime.datetime.fromisoformat(r["los"])
            max_elev = float(r["max_elev"])
            if max_elev >= ELEVATION_THRESHOLD:
                results.append((sat, aos, los, max_elev))
        except Exception:
            continue
    return results


def schedule_passes(pass_list):
    for sat, aos, los, _ in pass_list:
        local_start = (aos.astimezone() - datetime.timedelta(seconds=START_EARLY))
        time_str = local_start.strftime("%H:%M")
        schedule.every().day.at(time_str).do(record_pass, sat, aos, los)
        log_and_print("info", f"📅 Scheduled {sat} at {local_start:%Y-%m-%d %H:%M:%S} for {(los - aos).seconds}s.")


def auto_update_tle():
    config_data = load_config_data()
    if not config_data.get("latitude") or not config_data.get("longitude"):
        return log_and_print("warning", "No location set — skipping TLE refresh.")

    tle_data = []
    for s in tle_utils.TLE_SOURCES:
        tle = tle_utils.fetch_tle(s)
        if tle:
            tle_data.append(tle)
            log_and_print("info", f"✅ Updated TLE for {s}")
        else:
            log_and_print("warning", f"⚠ No TLE found for {s}")

    tle_utils.save_tle(tle_data)

    lat = config_data["latitude"]
    lon = config_data["longitude"]
    alt = config_data.get("altitude", 0)
    tz = config_data.get("timezone", "UTC")
    passes_utils.generate_predictions(lat, lon, alt, tz, "app/static/tle/active.txt")
    log_and_print("info", "📅 Pass predictions updated for next 24h.")


def listen_for_keypress():
    try:
        while True:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0] and sys.stdin.read(1).lower() == "x":
                SETTINGS_FILE.write_text(json.dumps({"recording_enabled": False}))
                sys.exit(0)
            time.sleep(0.1)
    except Exception:
        return


if __name__ == "__main__":
    logger.info("Scheduler starting up — running prechecks...")

    if not recordings_enabled():
        sys.exit(0)

    if not sdr.sdr_exists():
        SETTINGS_FILE.write_text(json.dumps({"recording_enabled": False}))
        sys.exit(1)

    auto_update_tle()
    schedule.every(6).hours.do(auto_update_tle)

    pass_list = load_pass_predictions(PASS_FILE)
    if not pass_list:
        log_and_print("warning", "No passes found in the next 24h — exiting.")
        sys.exit(0)

    log_and_print("info", f"{len(pass_list)} passes found — scheduling...")
    schedule_passes(pass_list)

    threading.Thread(target=listen_for_keypress, daemon=True).start()

    # ✅ Main loop with countdown
    while True:
        if not recordings_enabled():
            break

        schedule.run_pending()

        next_job = schedule.next_run()
        if next_job:
            delta = next_job - datetime.datetime.now().astimezone()
            countdown = f"⏳ Next job in {int(delta.total_seconds())}s at {next_job.strftime('%H:%M:%S')}"
            log_and_print("info", countdown)

        time.sleep(5)
        
