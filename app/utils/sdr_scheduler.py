import csv, datetime, time, subprocess, json, sys, threading, select, shutil, psutil, schedule
from pathlib import Path
from logging.handlers import RotatingFileHandler
import logging
import sdr

# --- CONFIG ---
SAT_FREQ = {"ISS": 145.800e6, "NOAA-19": 137.100e6}
RECORDINGS_DIR = Path("recordings")
LOG_DIR = Path("logs")
SETTINGS_FILE = Path("settings.json")
PASS_FILE = "predicted_passes.csv"
SAMPLE_RATE, GAIN = 48000, 27.9
ELEVATION_THRESHOLD, START_EARLY, STOP_LATE = 0, 30, 30
GREEN, RED, RESET = "\033[92m", "\033[91m", "\033[0m"

RECORDINGS_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("sstv_scheduler")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_DIR / "scheduler.log", maxBytes=1_000_000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)

def log_and_print(level, msg, pass_logger=None):
    if level == "info" and "Next job in" in msg:
        print(f"\r{msg}", end="", flush=True)
    else:
        print(msg)
    getattr(logger, level)(msg)
    if pass_logger:
        getattr(pass_logger, level)(msg)

def create_pass_logger(path):
    plogger = logging.getLogger(path.stem)
    if not plogger.handlers:
        h = RotatingFileHandler(path, maxBytes=200_000, backupCount=1)
        h.setFormatter(handler.formatter)
        plogger.addHandler(h)
    plogger.setLevel(logging.INFO)
    return plogger

def recordings_enabled():
    try:
        return json.load(SETTINGS_FILE.open()).get("recording_enabled", False)
    except FileNotFoundError:
        return False

def record_pass(sat, aos, los):
    start_str = aos.strftime("%Y%m%d_%H%M")
    wav_path = RECORDINGS_DIR / f"{start_str}_{sat}.wav"
    log_path = RECORDINGS_DIR / f"{start_str}_{sat}.log"
    plog = create_pass_logger(log_path)

    if not sdr.sdr_exists():
        log_and_print("warning", f"[{sat}] SDR not detected — skipping.", plog)
        return

    freq_key = sat.split()[0]
    freq = SAT_FREQ.get(freq_key)
    if not freq:
        log_and_print("warning", f"[{sat}] No frequency configured — skipping.", plog)
        return

    duration = int((los - aos).total_seconds()) + STOP_LATE
    log_and_print("info", f"[{sat}] ▶ Recording for {duration}s at {freq/1e6} MHz...", plog)

    cmd = ["rtl_fm", "-f", str(int(freq)), "-M", "fm", "-s", str(SAMPLE_RATE), "-g", str(GAIN)]
    sox_cmd = ["sox", "-t", "raw", "-r", str(SAMPLE_RATE), "-e", "signed", "-b", "16", "-c", "1", "-", str(wav_path)]

    error = None
    try:
        fm = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        sox = subprocess.Popen(sox_cmd, stdin=fm.stdout)
        time.sleep(duration)
    except Exception as e:
        error = str(e)
        log_and_print("error", f"[{sat}] Recording failed: {e}", plog)
    finally:
        fm.terminate()
        sox.terminate()
        log_and_print("info", f"[{sat}] ✔ Saved to {wav_path}", plog)

        size = wav_path.stat().st_size / (1024 * 1024) if wav_path.exists() else 0
        summary = [
            "", "===== PASS SUMMARY =====",
            f"Satellite: {sat}", f"Start (AOS): {aos}", f"End (LOS):   {los}",
            f"Duration:    {duration} seconds", f"Frequency:   {freq/1e6} MHz",
            f"SDR Present: True", f"File Size:   {size:.2f} MB",
            f"Errors:      {error if error else 'None'}", "========================", ""
        ]
        for line in summary:
            log_and_print("info", line, plog)

        verdict = "PASS" if not error and size > 0 else "FAIL"
        colour = GREEN if verdict == "PASS" else RED
        print(f"{colour}[{sat}] PASS COMPLETE — Verdict: {verdict} — File: {size:.2f} MB{RESET}")

def load_pass_predictions(path):
    passes = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            sat = row["satellite"]
            aos = datetime.datetime.fromisoformat(row["aos"])
            los = datetime.datetime.fromisoformat(row["los"])
            elev = float(row["max_elev"])
            if elev >= ELEVATION_THRESHOLD:
                passes.append((sat, aos, los, elev))
    return passes

def schedule_passes(pass_list):
    for sat, aos, los, _ in pass_list:
        start = aos - datetime.timedelta(seconds=START_EARLY)
        local_start = start.astimezone()
        schedule.every().day.at(local_start.strftime("%H:%M")).do(record_pass, sat, aos, los)
        log_and_print("info", f"📅 Scheduled {sat} at {local_start:%Y-%m-%d %H:%M:%S} {local_start.tzname()} "
                              f"for {(los - aos).seconds}s.")

def debug_monitor():
    now = datetime.datetime.now()
    jobs = schedule.get_jobs()
    if jobs:
        next_run = min(job.next_run for job in jobs)
        countdown = (next_run - now).total_seconds()
        h, rem = divmod(int(countdown), 3600)
        m, s = divmod(rem, 60)
        local_next = next_run.astimezone()
        msg = f"[{now:%H:%M:%S}] Next job in {h}h {m}m {s}s ({local_next:%H:%M:%S} {local_next.tzname()}) — Press X to stop"
    else:
        msg = f"[{now:%H:%M:%S}] No jobs scheduled — Press X to stop"
    print(f"\r{msg}", end="", flush=True)

def listen_for_keypress():
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.read(1).lower() == 'x':
                log_and_print("info", "❌ 'x' pressed — disabling recordings and exiting.")
                SETTINGS_FILE.write_text(json.dumps({"recording_enabled": False}))
                sys.exit(0)

if __name__ == "__main__":
    logger.info("Scheduler starting up — running prechecks...")
    if not recordings_enabled():
        log_and_print("info", "Recording disabled in settings.json — exiting.")
        sys.exit(0)
    if not sdr.sdr_exists():
        log_and_print("error", "No SDR detected — exiting.")
        log_and_print("info", "Recording disabled due to missing SDR.")
        SETTINGS_FILE.write_text(json.dumps({"recording_enabled": False}))
        sys.exit(1)

    passes = load_pass_predictions(PASS_FILE)
    if not passes:
        log_and_print("warning", "No qualifying passes predicted — exiting.")
        sys.exit(0)

    log_and_print("info", f"{len(passes)} passes found — scheduling...")
    schedule_passes(passes)
    print("Press X to stop recording scheduler.")
    threading.Thread(target=listen_for_keypress, daemon=True).start()

    while True:
        if not recordings_enabled():
            log_and_print("info", "Recording disabled via web — shutting down.")
            break
        schedule.run_pending()
        debug_monitor()
        time.sleep(5)
    
