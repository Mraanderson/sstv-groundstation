import csv, datetime, time, subprocess, json, sys, threading, select, psutil, schedule, logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.utils import sdr, tle as tle_utils, passes as passes_utils
from app import config_paths

# --- CONFIG ---
SAT_FREQ = {"ISS": 145.800e6, "NOAA-19": 137.100e6}
RECORDINGS_DIR, LOG_DIR, SETTINGS_FILE = Path("recordings"), Path("logs"), Path("settings.json")
PASS_FILE, SAMPLE_RATE, GAIN = "predicted_passes.csv", 48000, 27.9
ELEVATION_THRESHOLD, START_EARLY, STOP_LATE = 0, 30, 30
GREEN, RED, RESET = "\033[92m", "\033[91m", "\033[0m"
RECORDINGS_DIR.mkdir(exist_ok=True); LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("sstv_scheduler"); logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_DIR / "scheduler.log", maxBytes=1_000_000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)

def load_config_data():
    f = Path(config_paths.CONFIG_FILE)
    return json.load(open(f)) if f.exists() else {}

def log_and_print(level, msg, plog=None):
    print(msg if "Next job" not in msg else f"\r{msg}", end="", flush=True)
    getattr(logger, level)(msg); 
    if plog: getattr(plog, level)(msg)

def recordings_enabled():
    try: return SETTINGS_FILE.exists() and json.load(open(SETTINGS_FILE)).get("recording_enabled", False)
    except: return False

def write_metadata(start_str, sat, aos, los, freq_hz, dur, size, verdict, error):
    meta = {"satellite": sat, "timestamp": aos.isoformat(), "aos": aos.isoformat(), "los": los.isoformat(),
            "frequency": round(freq_hz/1e6,3), "mode":"FM","duration_s":dur,"file_mb":round(size,2),
            "verdict":verdict,"sstv_detected":False,"callsigns":[],"error":error or None}
    (RECORDINGS_DIR/f"{start_str}_{sat}.json").write_text(json.dumps(meta, indent=2))

def record_pass(sat,aos,los):
    start_str=aos.strftime("%Y%m%d_%H%M"); wav=RECORDINGS_DIR/f"{start_str}_{sat}.wav"
    plog=logging.getLogger(start_str); plog.setLevel(logging.INFO)
    plog.addHandler(RotatingFileHandler(RECORDINGS_DIR/f"{start_str}_{sat}.log",maxBytes=200_000,backupCount=1))
    if not sdr.sdr_exists(): return log_and_print("warning",f"[{sat}] SDR not detected — skipping.",plog)
    freq=SAT_FREQ.get(sat.split()[0]); 
    if not freq: return log_and_print("warning",f"[{sat}] No frequency configured — skipping.",plog)
    dur=int((los-aos).total_seconds())+STOP_LATE; log_and_print("info",f"[{sat}] ▶ Recording {dur}s at {freq/1e6:.3f} MHz",plog)
    error=None; fm=sox=None
    try:
        fm=subprocess.Popen(["rtl_fm","-f",str(int(freq)),"-M","fm","-s",str(SAMPLE_RATE),"-g",str(GAIN)],stdout=subprocess.PIPE)
        sox=subprocess.Popen(["sox","-t","raw","-r",str(SAMPLE_RATE),"-e","signed","-b","16","-c","1","-",str(wav)],stdin=fm.stdout)
        time.sleep(dur)
    except Exception as e: error=str(e)
    finally:
        for p in (sox,fm):
            try: p.terminate()
            except: pass
        size=wav.stat().st_size/(1024*1024) if wav.exists() else 0.0
        verdict="PASS" if not error and size>0 else "FAIL"
        print(f"{GREEN if verdict=='PASS' else RED}[{sat}] PASS COMPLETE — {verdict} — {size:.2f} MB{RESET}")
        write_metadata(start_str,sat,aos,los,freq,dur,size,verdict,error)

def load_pass_predictions(path):
    if not Path(path).exists(): return []
    return [(r["satellite"],datetime.datetime.fromisoformat(r["aos"]),
             datetime.datetime.fromisoformat(r["los"]),float(r["max_elev"]))
            for r in csv.DictReader(open(path)) if float(r["max_elev"])>=ELEVATION_THRESHOLD]

def schedule_passes(passes):
    for sat,aos,los,_ in passes:
        start=(aos.astimezone()-datetime.timedelta(seconds=START_EARLY))
        schedule.every().day.at(start.strftime("%H:%M")).do(record_pass,sat,aos,los)
        log_and_print("info",f"📅 Scheduled {sat} at {start:%Y-%m-%d %H:%M:%S} for {(los-aos).seconds}s.")

def auto_update_tle():
    cfg=load_config_data()
    if not cfg.get("latitude") or not cfg.get("longitude"): return log_and_print("warning","No location set — skipping TLE refresh.")
    tle_data=[tle for s in tle_utils.TLE_SOURCES if (tle:=tle_utils.fetch_tle(s))]
    tle_utils.save_tle(tle_data)
    passes_utils.generate_predictions(cfg["latitude"],cfg["longitude"],cfg.get("altitude",0),cfg.get("timezone","UTC"),"app/static/tle/active.txt")
    log_and_print("info","📅 Pass predictions updated for next 24h.")

def listen_for_keypress():
    try:
        while True:
            if sys.stdin in select.select([sys.stdin],[],[],0)[0] and sys.stdin.read(1).lower()=="x":
                SETTINGS_FILE.write_text(json.dumps({"recording_enabled":False})); sys.exit(0)
            time.sleep(0.1)
    except: return

if __name__=="__main__":
    logger.info("Scheduler starting up — running prechecks...")
    if not recordings_enabled(): sys.exit(0)
    if not sdr.sdr_exists(): SETTINGS_FILE.write_text(json.dumps({"recording_enabled":False})); sys.exit(1)
    auto_update_tle(); schedule.every(6).hours.do(auto_update_tle)
    passes=load_pass_predictions(PASS_FILE)
    if not passes: log_and_print("warning","No passes found — exiting."); sys.exit(0)
    log_and_print("info",f"{len(passes)} passes found — scheduling..."); schedule_passes(passes)
    threading.Thread(target=listen_for_keypress,daemon=True).start()
    while True:
        if not recordings_enabled(): break
        schedule.run_pending()
        if (nj:=schedule.next_run()):
            delta=nj-datetime.datetime.now()  # ✅ both naive
            log_and_print("info",f"⏳ Next job in {int(delta.total_seconds())}s at {nj.strftime('%H:%M:%S')}")
        time.sleep(5)
        
