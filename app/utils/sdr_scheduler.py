import csv
import datetime
import time
import schedule
import subprocess
from pathlib import Path
import shutil
import psutil
import logging
import json
import sys
from logging.handlers import RotatingFileHandler
import sdr  # your existing SDR detection module

# --- CONFIG ---
SAT_FREQ = {
    "ISS": 145.800e6,
    "NOAA-19": 137.100e6
}
RECORDINGS_DIR = Path("recordings")
LOG_DIR = Path("logs")
SETTINGS_FILE = Path("settings.json")
SAMPLE_RATE = 48000
GAIN = 40
ELEVATION_THRESHOLD = 20
START_EARLY = 30
STOP_LATE = 30
PASS_FILE = "predicted_passes.csv"

# ANSI colours
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

# --- SETUP ---
RECORDINGS_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Main rotating log
logger = logging.getLogger("sstv_scheduler")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_DIR / "scheduler.log",
                              maxBytes=1_000_000, backupCount=5)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_and_print(level, msg, pass_logger=None):
    """Log to main log, optional per-pass log, and print."""
    print(msg)
    getattr(logger, level)(msg)
    if pass_logger:
        getattr(pass_logger, level)(msg)

def create_pass_logger(log_path):
    """Create a rotating logger for a specific pass."""
    plogger = logging.getLogger(log_path.stem)
    plogger.setLevel(logging.INFO)
    if not plogger.handlers:
        phandler = RotatingFileHandler(log_path, maxBytes=200_000, backupCount=1)
        phandler.setFormatter(formatter)
        plogger.addHandler(phandler)
    return plogger

def recordings_enabled():
    """Check settings.json for recording_enabled flag."""
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f).get("recording_enabled", False)
    except FileNotFoundError:
        return False

# --- FUNCTIONS ---
def record_pass(sat_name, aos, los):
    start_str = aos.strftime("%Y%m%d_%H%M")
    wav_path = RECORDINGS_DIR / f"{start_str}_{sat_name}.wav"
    pass_log_path = RECORDINGS_DIR / f"{start_str}_{sat_name}.log"
    pass_logger = create_pass_logger(pass_log_path)

    sdr_status = sdr.sdr_exists()
    if not sdr_status:
        log_and_print("warning", f"[{sat_name}] SDR not detected — skipping.", pass_logger)
        return

    freq = SAT_FREQ.get(sat_name)
    if not freq:
        log_and_print("warning", f"[{sat_name}] No frequency configured — skipping.", pass_logger)
        return

    duration = int((los - aos).total_seconds()) + STOP_LATE
    log_and_print("info", f"[{sat_name}] ▶ Recording for {duration}s at {freq/1e6} MHz...", pass_logger)

    cmd = [
        "rtl_fm",
        "-f", str(int(freq)),
        "-M", "fm",
        "-s", str(SAMPLE_RATE),
        "-g", str(GAIN)
    ]
    sox_cmd = [
        "sox", "-t", "raw", "-r", str(SAMPLE_RATE),
        "-e", "signed", "-b", "16", "-c", "1", "-",
        str(wav_path)
    ]

    error_flag = None
    try:
        fm_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        sox_proc = subprocess.Popen(sox_cmd, stdin=fm_proc.stdout)
        time.sleep(duration)
    except Exception as e:
        error_flag = str(e)
        log_and_print("error", f"[{sat_name}] Recording failed: {e}", pass_logger)
    finally:
        fm_proc.terminate()
        sox_proc.terminate()
        log_and_print("info", f"[{sat_name}] ✔ Saved to {wav_path}", pass_logger)

        # --- SUMMARY FOOTER ---
        file_size_mb = wav_path.stat().st_size / (1024 * 1024) if wav_path.exists() else 0
        summary_lines = [
            "",
            "===== PASS SUMMARY =====",
            f"Satellite: {sat_name}",
            f"Start (AOS): {aos}",
            f"End (LOS):   {los}",
            f"Duration:    {duration} seconds",
            f"Frequency:   {freq/1e6} MHz",
            f"SDR Present: {sdr_status}",
            f"File Size:   {file_size_mb:.2f} MB",
            f"Errors:      {error_flag if error_flag else 'None'}",
            "========================",
            ""
        ]
        for line in summary_lines:
            log_and_print("info", line, pass_logger)

        verdict = "PASS" if not error_flag and file_size_mb > 0 else "FAIL"
        colour = GREEN if verdict == "PASS" else RED
        print(f"{colour}[{sat_name}] PASS COMPLETE — Verdict: {verdict} — File: {file_size_mb:.2f} MB{RESET}")

def load_pass_predictions(csv_path):
    passes = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sat_name = row["satellite"]
            aos = datetime.datetime.fromisoformat(row["aos"])
            los = datetime.datetime.fromisoformat(row["los"])
            max_elev = float(row["max_elev"])
            if max_elev >= ELEVATION_THRESHOLD:
                passes.append((sat_name, aos, los, max_elev))
    return passes

def schedule_passes(pass_list):
    for sat_name, aos, los, _ in pass_list:
        start_time = aos - datetime.timedelta(seconds=START_EARLY)
        schedule.every().day.at(start_time.strftime("%H:%M")).do(
            record_pass, sat_name, aos, los
        )
        log_and_print("info", f"📅 Scheduled {sat_name} at {start_time} "
                              f"for {(los - aos).seconds}s.")

def debug_monitor():
    now = datetime.datetime.now()
    jobs = schedule.get_jobs()
    if jobs:
        next_run = min(job.next_run for job in jobs)
        countdown = (next_run - now).total_seconds()
        log_and_print("info", f"[{now:%H:%M:%S}] Next job in {countdown:.0f}s "
                              f"({next_run.time()})")
    else:
        log_and_print("info", f"[{now:%H:%M:%S}] No jobs scheduled.")

    log_and_print("info", f"SDR connected: {sdr.sdr_exists()}")
    total, used, free = shutil.disk_usage(RECORDINGS_DIR)
    log_and_print("info", f"Disk free: {free // (1024*1024)} MB")
    log_and_print("info", f"CPU load: {psutil.cpu_percent()}%")
    log_and_print("info", "-" * 40)

# --- MAIN ---
if __name__ == "__main__":
    logger.info("Scheduler starting up — running prechecks...")

    # Precheck: recordings enabled
    if not recordings_enabled():
        log_and_print("info", "Recording disabled in settings.json — exiting.")
        sys.exit(0)

    # Precheck: SDR present
    if not sdr.sdr_exists():
        log_and_print("error", "No SDR detected — exiting.")
        sys.exit(1)

    # Precheck: passes available
    passes = load_pass_predictions(PASS_FILE)
    if not passes:
        log_and_print("warning", "No qualifying passes predicted — exiting.")
        sys.exit(0)

    log_and_print("info", f"{len(passes)} passes found — scheduling...")
    schedule_passes(passes)

    while True:
        if not recordings_enabled():
            log_and_print("info", "Recording disabled via web — shutting down.")
            break
        schedule.run_pending()
        debug_monitor()
        time.sleep(5)
        
