import csv, datetime, time, subprocess, json, sys, threading, select, psutil, schedule, logging, re, os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.utils import sdr, tle as tle_utils, passes as passes_utils
from app import config_paths

# --- CONFIG ---
SAT_FREQ = {"ISS": 145.800e6}
RECORDINGS_DIR, LOG_DIR, SETTINGS_FILE = Path("recordings"), Path("logs"), Path("settings.json")
PASS_FILE, SAMPLE_RATE, GAIN = "predicted_passes.csv", 48000, 29.7
ELEVATION_THRESHOLD, START_EARLY, STOP_LATE = 0, 30, 30
GREEN, RED, RESET = "\033[92m", "\033[91m", "\033[0m"
RECORDINGS_DIR.mkdir(exist_ok=True); LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("sstv_scheduler"); logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_DIR / "scheduler.log", maxBytes=1_000_000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)

# --- Pass state file for diagnostics ---
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

# --- Helpers ---
def load_config_data():
    f = Path(config_paths.CONFIG_FILE)
    return json.load(open(f)) if f.exists() else {}

def log_and_print(level, msg, plog=None):
    print(msg if "Next job" not in msg else f"\r{msg}", end="", flush=True)
    getattr(logger, level)(msg)
    if plog: getattr(plog, level)(msg)

def recordings_enabled():
    try:
        return SETTINGS_FILE.exists() and json.load(open(SETTINGS_FILE)).get("recording_enabled", False)
    except:
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

# --- Main recording function ---
def record_pass(sat, aos, los):
    start_str = aos.strftime("%Y%m%d_%H%M")
    safe_sat = re.sub(r'[^A-Za-z0-9_-]', '_', sat)

    freq = SAT_FREQ.get(sat.split()[0].replace(" ", "-"))
    if not freq:
        return log_and_print("warning", f"[{sat}] No frequency configured — skipping.")

    freq_mhz = f"{freq/1e6:.3f}MHz"
    base_name = f"{start_str}_{safe_sat}_{freq_mhz}"
    wav = RECORDINGS_DIR / f"{base_name}.wav"
    iqfile = RECORDINGS_DIR / f"{base_name}.iq"

    plog = logging.getLogger(start_str); plog.setLevel(logging.INFO)
    plog.addHandler(RotatingFileHandler(RECORDINGS_DIR/f"{base_name}.log",
                                        maxBytes=200_000, backupCount=1))

    if not sdr.sdr_exists():
        return log_and_print("warning", f"[{sat}] SDR not detected — skipping.", plog)

    # Disk space check (≥ 3 GB free)
    statvfs = os.statvfs(str(RECORDINGS_DIR))
    free_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
    if free_gb < 3:
        return log_and_print("warning", f"[{sat}] Not enough disk space ({free_gb:.2f} GB free) — skipping.", plog)

    dur = int((los - aos).total_seconds()) + STOP_LATE
    log_and_print("info", f"[{sat}] ▶ IQ capture for {dur}s at {freq/1e6:.3f} MHz", plog)

    # Mark pass start for diagnostics
    mark_pass_start(sat, iqfile, los)

    error = None; size = 0.0
    try:
        subprocess.run([
            "rtl_sdr", "-f", str(int(freq)), "-s", "2048000",
            "-n", str(2048000 * dur), str(iqfile)
        ], check=True)

        subprocess.run([
            "sox", "-t", "raw", "-r", "2048000", "-e", "unsigned", "-b", "8", "-c", "2",
            str(iqfile), "-r", "48000", str(wav), "rate"
        ], check=True)

        subprocess.run([
            "sox", str(wav), "-n", "spectrogram", "-o", str(RECORDINGS_DIR / f"{base_name}.png")
        ], check=True)

        iqfile.unlink(missing_ok=True)
        size = wav.stat().st_size / (1024*1024) if wav.exists() else 0.0

    except Exception as e:
        error = str(e)

    verdict = "PASS" if not error and size > 0 else "FAIL"
    print(f"{GREEN if verdict=='PASS' else RED}[{sat}] PASS COMPLETE — {verdict} — {size:.2f} MB{RESET}")
    write_metadata(start_str, sat, aos, los, freq, dur, size, verdict, error, base_name)

    # Clear pass state
    mark_pass_end()
    def load_pass_predictions(path):
    if not Path(path).exists():
        return []
    results = []
    for r in csv.DictReader(open(path)):
        try:
            sat = r["satellite"]
            aos = datetime.datetime.fromisoformat(r["aos"]).astimezone()
            los = datetime.datetime.fromisoformat(r["los"]).astimezone()
            max_elev = float(r["max_elev"])
            if max_elev >= ELEVATION_THRESHOLD:
                results.append((sat, aos, los, max_elev))
        except Exception:
            continue
    return results

def schedule_passes(passes):
    for sat, aos, los, _ in passes:
        start = (aos - datetime.timedelta(seconds=START_EARLY))
        schedule.every().day.at(start.strftime("%H:%M")).do(record_pass, sat, aos, los)
        log_and_print("info",
            f"📅 Scheduled {sat} at {start:%Y-%m-%d %H:%M:%S} for {(los - aos).seconds}s."
        )

def auto_update_tle():
    cfg = load_config_data()
    if not cfg.get("latitude") or not cfg.get("longitude"):
        return log_and_print("warning", "No location set — skipping TLE refresh.")

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
    passes_utils.generate_predictions(
        cfg["latitude"], cfg["longitude"], cfg.get("altitude", 0),
        cfg.get("timezone", "UTC"), "app/static/tle/active.txt"
    )
    log_and_print("info", "📅 Pass predictions updated for next 24h.")

def listen_for_keypress():
    try:
        while True:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                if sys.stdin.read(1).lower() == "x":
                    SETTINGS_FILE.write_text(json.dumps({"recording_enabled": False}))
                    sys.exit(0)
            time.sleep(0.1)
    except:
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

    passes = load_pass_predictions(PASS_FILE)
    if not passes:
        log_and_print("warning", "No passes found — exiting.")
        sys.exit(0)

    log_and_print("info", f"{len(passes)} passes found — scheduling...")
    schedule_passes(passes)

    threading.Thread(target=listen_for_keypress, daemon=True).start()

    while True:
        if not recordings_enabled():
            break
        schedule.run_pending()
        if (nj := schedule.next_run()):
            delta = nj - datetime.datetime.now()
            log_and_print("info",
                f"⏳ Next job in {int(delta.total_seconds())}s at {nj.strftime('%H:%M:%S')}"
            )
        time.sleep(5)
    
