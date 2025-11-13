# Patch for sdr_scheduler.py - Recording Diagnostics Integration

## Summary
Add detailed logging and validation to the `record_pass()` function to expose:
1. Exact PPM being used
2. Complete rtl_fm + sox command before execution
3. WAV file validation after recording
4. Comprehensive error messages

## Changes Required

### 1. Add Import at Top (line 1-8)
```python
import csv, datetime, time, subprocess, json, sys, threading, select, psutil, schedule, logging, re, os
from pathlib import Path
from zoneinfo import ZoneInfo
from logging.handlers import RotatingFileHandler
from app.utils import sdr, tle as tle_utils, passes as passes_utils
from app.utils.iq_cleanup import periodic_cleanup
from app.utils.sdr_diagnostics import log_recording_command, validate_wav_file  # ADD THIS LINE
from app import config_paths
```

### 2. Update record_pass() Function (line 96-155)

**BEFORE (current code - lines 130-150):**
```python
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
            f" -c 1 {wav}"
        )
        subprocess.run(cmd, shell=True, check=True)
```

**AFTER (with diagnostics):**
```python
    ppm = 0
    try:
        if SETTINGS_FILE.exists():
            ppm = json.loads(SETTINGS_FILE.read_text()).get("rtl_ppm", 0)
    except Exception as e:
        logger.warning(f"Could not load ppm: {e}")

    mark_pass_start(sat, wav, los)

    # Log recording parameters and command before execution
    log_recording_command(
        satellite=sat,
        frequency_hz=int(freq),
        frequency_mhz=freq/1e6,
        ppm=ppm,
        duration_s=dur,
        sample_rate=SAMPLE_RATE,
        gain=GAIN,
        output_wav=str(wav),
        logger_obj=plog
    )

    error = None; size = 0.0
    try:
        cmd = (
            f"timeout {dur+10} rtl_fm -f {int(freq)} -M fm -s {SAMPLE_RATE} "
            f"-g {GAIN} -l 0 -p {ppm} "
            f"| sox -t raw -r {SAMPLE_RATE} -e signed -b 16 -c 1 - "
            f"-c 1 {wav}"
        )
        log_and_print("info", f"[{sat}] Executing: {cmd}", plog)
        subprocess.run(cmd, shell=True, check=True)
        
        # Validate WAV file after recording
        validation = validate_wav_file(wav)
        if validation["valid"]:
            log_and_print("info", f"[{sat}] WAV validated: {validation['format']}, {validation['duration_s']}s", plog)
            size = validation["size_mb"]
        else:
            error = f"WAV validation failed: {validation['error']}"
            log_and_print("error", f"[{sat}] {error}", plog)
```

### 3. Improved Error Handling (line 145-155)

**BEFORE:**
```python
    except Exception as e:
        error = str(e)

    verdict = "PASS" if not error and size > 0 else "FAIL"
    #...
```

**AFTER:**
```python
    except Exception as e:
        error = str(e)
        log_and_print("error", f"[{sat}] Recording failed: {error}", plog)

    verdict = "PASS" if not error and size > 0 else "FAIL"
    log_and_print("info", f"[{sat}] PASS RESULT: {verdict}, Size: {size:.2f}MB, Error: {error or 'None'}", plog)
    #...
```

## Key Changes Explained

1. **Import sdr_diagnostics** - Brings in validation and logging utilities
2. **Call log_recording_command()** - Prints detailed params and full command BEFORE execution
3. **Longer timeout** - Changed from `dur` to `dur+10` to account for startup/shutdown
4. **Log command string** - Adds second log entry with the exact shell command being executed
5. **Validate WAV after** - Checks file integrity, format, and duration immediately after recording
6. **Enhanced error logging** - More context about what failed

## Testing the Patch

After applying, test with:

```bash
# Manual recording via web UI
# Go to Diagnostics → Manual Recorder
# Expected: logs show command and PPM used

# Check logs
tail -f logs/scheduler.log
tail -f recordings/manual/*.txt

# Validate a specific recording
python3 -c "
from pathlib import Path
from app.utils.sdr_diagnostics import validate_wav_file
result = validate_wav_file(Path('recordings/test.wav'))
import json
print(json.dumps(result, indent=2))
"
```

## Alternative: Use Subprocess Array Instead of Shell String

For better security/clarity, the command could be split (less risky than shell=True):

```python
    cmd_list = [
        "timeout", str(dur+10),
        "bash", "-c",
        f"rtl_fm -f {int(freq)} -M fm -s {SAMPLE_RATE} -g {GAIN} -l 0 -p {ppm} | "
        f"sox -t raw -r {SAMPLE_RATE} -e signed -b 16 -c 1 - -c 1 {wav}"
    ]
    subprocess.run(cmd_list, check=True)
```

Or even better with Popen+pipes like the manual_recorder does:
```python
    p1 = subprocess.Popen(
        ["rtl_fm", "-f", str(int(freq)), "-M", "fm", "-s", str(SAMPLE_RATE), 
         "-g", str(GAIN), "-l", "0", "-p", str(ppm)],
        stdout=subprocess.PIPE, stderr=plog
    )
    p2 = subprocess.Popen(
        ["sox", "-t", "raw", "-r", str(SAMPLE_RATE), "-e", "signed", "-b", "16", 
         "-c", "1", "-", "-c", "1", str(wav)],
        stdin=p1.stdout, stderr=plog
    )
    p1.stdout.close()
    p2.wait(timeout=dur+10)
```

This approach is safer and integrates stderr into the log file automatically.
