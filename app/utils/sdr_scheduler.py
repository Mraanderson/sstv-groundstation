import csv, datetime, time, subprocess, json, sys, threading, select, psutil, schedule, logging, re, os
from pathlib import Path
from zoneinfo import ZoneInfo
from logging.handlers import RotatingFileHandler
from app.utils import sdr, tle as tle_utils, passes as passes_utils
from app.utils.iq_cleanup import periodic_cleanup
from app import config_paths

# --- CONFIG ---
SAT_FREQ = {"ISS": 145.800e6}
RECORDINGS_DIR, LOG_DIR, SETTINGS_FILE = Path("recordings"), Path("logs"), Path("settings.json")
PASS_FILE, SAMPLE_RATE, GAIN = "predicted_passes.csv", 48000, 29.7
ELEVATION_THRESHOLD, START_EARLY, STOP_LATE = 0, 30, 30
GREEN, RED, RESET = "\033[92m", "\033[91m", "\033[0m"
RECORDINGS_DIR.mkdir(exist_ok=True); LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("sstv_scheduler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = RotatingFileHandler(LOG_DIR / "scheduler.log", maxBytes=1_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)

STATE_FILE = os.path.expanduser("~/sstv-groundstation/current_pass.json")

def mark_pass_start(sat, iq_file, los):
    data = {
        "satellite": sat,
        "iq_file": str(iq_file),
        "end_time": los.isoformat(),
        "started": datetime.datetime.now().isoformat()
    }
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"Could not write pass state: {e}")

def mark_pass_end():
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
    except Exception as e:
        logger.warning(f"Could not remove pass state: {e}")

def load_config_data():
    f = Path(config_paths.CONFIG_FILE)
    try:
        if f.exists():
            with open(f) as file:
                return json.load(file)
        else:
            return {}
    except Exception as e:
        logger.warning(f"Could not load config data: {e}")
        return {}

def log_and_print(level, msg, plog=None):
    print(msg if "Next job" not in msg else f"\r{msg}", end="", flush=True)
    getattr(logger, level)(msg)
    if plog: getattr(plog, level)(msg)

def recordings_enabled():
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE) as f:
                return json.load(f).get("recording_enabled", False)
        return False
    except Exception as e:
        logger.warning(f"Could not check if recordings are enabled: {e}")
        return False

def write_metadata(start_str, sat, aos, los, freq_hz, dur, size, verdict, error, base_name):
    meta = {
        "satellite": sat,
        "timestamp": aos.isoformat(),
        "aos": aos.isoformat(),
        "los": los.isoformat(),
        "frequency": round(freq_hz/1e6, 3),
        "mode": "FM",
        "duration_s": dur,
        "file_mb": round(size, 2),
        "verdict": verdict,
        "sstv_detected": False,
        "callsigns": [],
        "error": error or None,
        "files": {
            "wav": f"{base_name}.wav",
            "png": f"{base_name}.png",
            "log": f"{base_name}.log",
            "json": f"{base_name}.json"
        }
    }
    (RECORDINGS_DIR / f"{base_name}.json").write_text(json.dumps(meta, indent=2))

def record_pass(sat, aos, los):
    start_str = aos.strftime("%Y%m%d_%H%M")
    safe_sat = re.sub(r'[^A-Za-z0-9_-]', '_', sat)
    freq = SAT_FREQ.get(sat.split()[0].replace(" ", "-"))
    if not freq:
        return log_and_print("warning", f"[{sat}] No frequency configured — skipping.")
    freq_mhz = f"{freq/1e6:.3f}MHz"
    base_name = f"{start_str}_{safe_sat}_{freq_mhz}"
    wav = RECORDINGS_DIR / f"{base_name}.wav"

    plog = logging.getLogger(start_str)
    plog.setLevel(logging.INFO)
    plog.addHandler(RotatingFileHandler(RECORDINGS_DIR/f"{base_name}.log",
                                        maxBytes=200_000, backupCount=1))

    if not sdr.sdr_exists():
        return log_and_print("warning", f"[{sat}] SDR not detected — skipping.", plog)

    statvfs = os.statvfs(str(RECORDINGS_DIR))
    free_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
    if free_gb < 3:
        return log_and_print("warning", f"[{sat}] Not enough disk space ({free_gb:.2f} GB free) — skipping.", plog)

    dur = int((los - aos).total_seconds()) + STOP_LATE
    log_and_print("info", f"[{sat}] ▶ WAV capture for {dur}s at {freq/1e6:.3f} MHz", plog)

    ppm = 0
    try:
        if SETTINGS_FILE.exists():
            ppm = json.loads(SETTINGS_FILE.read_text()).get("rtl_ppm", 0)
    except Exception as e:
        logger.warning(f"Could not load ppm: {e}")

    mark_pass_start(sat, wav, los)

    error = None; size = 0.0
    try:
        cmd = (
            f"timeout {dur} rtl_fm -f {int(freq)} -M fm -s {SAMPLE_RATE} "
            f"-g {GAIN} -l 0 -p {ppm} "
            f"| sox -t raw -r {SAMPLE_RATE} -e signed -b 16 -c 1 - "
            f"-r 11025 -c 1 {wav}"
        )
        subprocess.run(cmd, shell=True, check=True)
        subprocess.run([
            "sox", str(wav), "-n", "spectrogram",
            "-o", str(RECORDINGS_DIR / f"{base_name}.png")
        ], check=True)
        size = wav.stat().st_size / (1024*1024) if wav.exists() else 0.0
    except Exception as e:
        error = str(e)

    verdict = "PASS" if not error and size > 0 else "FAIL"
    print(f"{GREEN if verdict=='PASS' else RED}[{sat}] PASS COMPLETE — {verdict} — {size:.2f} MB{RESET}")
    write_metadata(start_str, sat, aos, los, freq, dur, size, verdict, error, base_name)

def schedule_passes(passes):
    cfg = load_config_data()
    user_tz = cfg.get("timezone", "UTC")
    tzinfo = ZoneInfo(user_tz)
    for sat, aos, los, _ in passes:
        aos_local = aos.astimezone(tzinfo)
        start = (aos_local - datetime.timedelta(seconds=START_EARLY))
        schedule.every().day.at(start.strftime("%H:%M")).do(record_pass, sat, aos, los)
        log_and_print("info",
            f"📅 Scheduled {sat} at {start:%Y-%m-%d %H:%M:%S} {user_tz} for {(los - aos).seconds}s."
        )

def load_pass_predictions(path):
    """Read predicted_passes.csv and return list of (sat, aos, los, max_el)."""
    results = []
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    sat = row["satellite"]
                    aos = datetime.datetime.fromisoformat(row["aos"]).replace(tzinfo=ZoneInfo("UTC"))
                    los = datetime.datetime.fromisoformat(row["los"]).replace(tzinfo=ZoneInfo("UTC"))
                    max_el = float(row.get("max_elev", 0))
                    results.append((sat, aos, los, max_el))
                except Exception as e:
                    logger.warning(f"Skipping bad row in {path}: {e}")
    except FileNotFoundError:
        logger.warning(f"No pass file found at {path}")
    return results

def refresh_predictions():
    """Update TLEs, regenerate 48h of passes, and reschedule jobs."""
    cfg = load_config_data()
    if not cfg.get("latitude") or not cfg.get("longitude"):
        return log_and_print("warning", "No location set — skipping prediction refresh.")

    # Update TLEs (ISS shown as example; include others as needed)
    tle_data = []
    for s in tle_utils.TLE_SOURCES:
        if "ISS" in s.upper():
            tle = tle_utils.fetch_tle(s)
            if tle:
                tle_data.append(tle)
                log_and_print("info", f"✅ Updated TLE for {s}")
            else:
                log_and_print("warning", f"⚠ No TLE found for {s}")
    tle_utils.save_tle(tle_data)

    # Regenerate and overwrite CSV for next 48h from now
    passes_utils.generate_predictions(
        cfg["latitude"], cfg["longitude"], cfg.get("altitude", 0),
        cfg.get("timezone", "UTC"), "app/static/tle/active.txt", hours=48
    )

    # Reload CSV and reschedule jobs
    new_passes = load_pass_predictions(PASS_FILE)
    schedule.clear()  # clear all jobs
    if new_passes:
        log_and_print("info", f"📅 Predictions refreshed — {len(new_passes)} passes found.")
        schedule_passes(new_passes)
    else:
        log_and_print("warning", "No passes after refresh — will retry hourly.")

def listen_for_keypress():
    try:
        while True:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                if sys.stdin.read(1).lower() == "x":
                    try:
                        SETTINGS_FILE.write_text(json.dumps({"recording_enabled": False}))
                    except Exception as e:
                        logger.warning(f"Could not update settings file: {e}")
                    sys.exit(0)
            time.sleep(0.1)
    except Exception as e:
        logger.warning(f"Error in keypress listener: {e}")
        return

# Allow manual refresh from Flask by importing this function
def manual_refresh():
    """Public entry point for Flask route to trigger a refresh."""
    refresh_predictions()
    return {"ok": True}

if __name__ == "__main__":
    threading.Thread(target=periodic_cleanup, kwargs={"interval_minutes":30}, daemon=True).start()
    logger.info("Scheduler starting up — running prechecks...")
    if not recordings_enabled():
        sys.exit(0)
    if not sdr.sdr_exists():
        SETTINGS_FILE.write_text(json.dumps({"recording_enabled": False}))
        sys.exit(1)

    # Initial refresh and hourly rolling refresh
    refresh_predictions()
    schedule.every(1).hours.do(refresh_predictions)

    # Load passes defensively; if empty, try one more refresh
    passes = load_pass_predictions(PASS_FILE)
    if not passes:
        log_and_print("warning", "No passes found — forcing secondary refresh.")
        refresh_predictions()
        passes = load_pass_predictions(PASS_FILE)

    if not passes:
        log_and_print("warning", "Still no passes — exiting. Next hourly refresh may recover.")
        sys.exit(0)

    log_and_print("info", f"{len(passes)} passes found — scheduling...")
    schedule_passes(passes)

    threading.Thread(target=listen_for_keypress, daemon=True).start()

    while True:
        if not recordings_enabled():
            break
        schedule.run_pending()
        if (nj := schedule.next_run()):
            cfg = load_config_data()
            user_tz = cfg.get("timezone", "UTC")
            tzinfo = ZoneInfo(user_tz)
            now_local = datetime.datetime.now(tzinfo)
            nj_local = nj.replace(tzinfo=tzinfo)
            delta = (nj_local - now_local)
            log_and_print("info",
                f"⏳ Next job in {int(delta.total_seconds())}s at {nj_local.strftime('%H:%M:%S')} {user_tz}"
            )
        time.sleep(5)
        
