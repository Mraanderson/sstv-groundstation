# Quick Start: Apply Recording Diagnostics

## What's Been Done ✅
- Created `app/utils/sdr_diagnostics.py` with validation utilities
- Documented root causes in `RECORDING_DEBUG.md`
- Provided detailed patch in `SCHEDULER_PATCH.md`
- UI recommendations in `UI_ENHANCEMENTS.md`
- Full summary in `RECORDING_FIX_SUMMARY.md`

## What You Need to Do

### Step 1: Update sdr_scheduler.py (5 minutes)

**File:** `app/utils/sdr_scheduler.py`

**Add import** (line 7):
```python
from app.utils.sdr_diagnostics import log_recording_command, validate_wav_file
```

**In `record_pass()` function, line ~132 (after `mark_pass_start()`):**

Replace this:
```python
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

With this:
```python
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

**In `record_pass()` function, line ~150 (error handling):**

Update the error handling to add more logging:
```python
    except Exception as e:
        error = str(e)
        log_and_print("error", f"[{sat}] Recording failed: {error}", plog)

    verdict = "PASS" if not error and size > 0 else "FAIL"
    log_and_print("info", f"[{sat}] RESULT: {verdict} | Size: {size:.2f}MB | Error: {error or 'None'}", plog)
```

### Step 2: Test It

**Manual Recording Test:**
```bash
# Go to web UI
# Diagnostics → Manual Recorder
# Set frequency to 145.800M
# Set duration to 30
# Click Record
# Check /tmp/manual_recorder.log for command visibility
```

**Check Logs:**
```bash
# Watch scheduler logs
tail -f logs/scheduler.log

# Should see output like:
# ======================================================================
# [ISS] Recording Parameters:
#   Frequency:    145.800 MHz (145800000 Hz)
#   PPM Correction: 0 ppm
#   ...
# ======================================================================
```

**Verify File Validation:**
```python
from pathlib import Path
from app.utils.sdr_diagnostics import validate_wav_file

result = validate_wav_file(Path('recordings/20251115_1430_ISS_145.800MHz.wav'))
print(result)
# Should show:
# {'valid': True, 'format': '16-bit mono 48000 Hz', 'duration_s': 623.5, ...}
```

### Step 3: Enable Recordings

```bash
# Via web UI:
# 1. Recordings → Enable
# 2. Wait for next pass
# 3. Check logs: tail -f logs/scheduler.log
# 4. Look for the command being logged
# 5. Look for WAV validation result
```

---

## Files Modified

- ✅ **Created:** `app/utils/sdr_diagnostics.py` (new diagnostic module)
- ✏️ **Edit:** `app/utils/sdr_scheduler.py` (add logging and validation)
- 📄 **Reference:** `SCHEDULER_PATCH.md` (exact changes needed)

---

## Expected Behavior After Changes

### Before Logging
```
[ISS] ▶ WAV capture for 600s at 145.800 MHz
[ISS] PASS COMPLETE — FAIL — 0.00 MB
```

### After Logging
```
======================================================================
[ISS] Recording Parameters:
  Frequency:    145.800 MHz (145800000 Hz)
  PPM Correction: 0 ppm
  Sample Rate:  48000 Hz
  Gain:         29.7 dB
  Duration:     600 seconds (timeout: 610s)
  Output:       recordings/20251115_1430_ISS_145.800MHz.wav
──────────────────────────────────────────────────────────────────────
Full Command:
  timeout 610 rtl_fm -f 145,800,000 -M fm -s 48,000 -g 29.7 -l 0 -p 0 | sox -t raw -r 48,000 -e signed -b 16 -c 1 - -c 1 recordings/20251115_1430_ISS_145.800MHz.wav
======================================================================
Executing: timeout 610 rtl_fm -f 145800000 -M fm -s 48000 -g 29.7 -l 0 -p 0 | sox -t raw -r 48000 -e signed -b 16 -c 1 - -c 1 recordings/20251115_1430_ISS_145.800MHz.wav
[ISS] WAV validated: 16-bit mono 48000 Hz, 623.5s
[ISS] RESULT: PASS | Size: 45.23MB | Error: None
```

---

## Troubleshooting

### If you get import errors:
```
ModuleNotFoundError: No module named 'app.utils.sdr_diagnostics'
```
→ Make sure you created the file at `app/utils/sdr_diagnostics.py`

### If validation shows "Empty WAV file":
→ Check PPM value: `cat settings.json | grep rtl_ppm`  
→ Check frequency is correct  
→ Run Diagnostics → Calibrate SDR first

### If you see "Permission denied":
→ Run: `sudo usermod -a -G dialout $USER` and logout/login

---

## Success Criteria

After applying these changes, you should be able to:

✅ See the complete rtl_fm command in logs BEFORE it runs  
✅ See the PPM value being used for each recording  
✅ See WAV file validation result after recording (format, duration, size)  
✅ Understand why a recording failed (command visibility + validation)  
✅ Create complete .wav files for full ISS passes  

---

## Time Estimate

- Code changes: **5 minutes** (copy/paste from SCHEDULER_PATCH.md)
- Testing: **10 minutes** (manual test + log review)
- Full integration: **15 minutes**

---

## Questions?

Refer to:
- **Root causes:** `RECORDING_DEBUG.md`
- **Detailed patch:** `SCHEDULER_PATCH.md`
- **UI improvements:** `UI_ENHANCEMENTS.md`
- **Full summary:** `RECORDING_FIX_SUMMARY.md`
