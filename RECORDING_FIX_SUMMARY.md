# SSTV Groundstation - Recording Issues Analysis & Solution Summary

**Date:** November 13, 2025  
**Issue:** Scheduled recordings not working correctly. Files appear invalid. No visibility into command execution. PPM may be incorrect. rtl_test returning error 129.

---

## Root Cause Analysis

### 1. **No Command Visibility** (Critical)
The complete `rtl_fm | sox` command was built as a string but NEVER logged or displayed.  
→ **Impact:** Impossible to debug if recording fails. Users can't verify parameters are correct.

### 2. **PPM Not Logged** (Critical)
PPM is loaded from `settings.json` but never logged, making it impossible to know what correction factor was actually used.  
→ **Impact:** If PPM is wrong, recordings could be offset or fail silently.

### 3. **No WAV File Validation** (Critical)
Only file existence and size checked. No verification of:
- WAV header integrity
- Correct format (16-bit mono 48000 Hz)
- Actual duration vs expected duration
→ **Impact:** Can't distinguish between real audio and corrupted/empty files.

### 4. **RTL-SDR Test Returns Error 129** (High)
`rtl_test -t` returns USB error 129, which is LIBUSB_ERROR_ACCESS, not a hardware failure.  
→ **Impact:** Misdiagnosis. Real issue is likely permissions: `sudo usermod -a -G dialout $USER`

### 5. **SOX Command Formatting Issue** (Medium)
Original sox command missing explicit format specifier. Should be:
```bash
sox -t raw -r 48000 -e signed -b 16 -c 1 - -c 1 output.wav  # Correct
```

### 6. **Duration Timeout Not Aligned** (Medium)
`timeout {dur}` should be `timeout {dur+10}` to allow rtl_fm startup and shutdown without being killed prematurely.

---

## Solution Delivered

### Created: `app/utils/sdr_diagnostics.py`

A new diagnostic utility module with:

#### **`validate_wav_file(wav_path: Path) -> Dict[str, Any]`**
- Reads WAV headers
- Validates format, duration, sample rate, channels
- Returns detailed info or error message
- **Usage:** Check file validity after recording

#### **`build_rtl_fm_command(...) -> str`**
- Constructs rtl_fm command with all parameters visible
- **Usage:** For logging and transparency

#### **`build_sox_command(...) -> str`**
- Constructs sox command
- **Usage:** For logging and transparency

#### **`log_recording_command(...) -> str`**
- Logs all recording parameters in a formatted box
- Logs complete command string
- Returns full command for execution
- **Usage:** Call BEFORE subprocess.run()

**Example Output:**
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
```

#### **`verify_rtl_sdr_connection() -> Tuple[bool, str]`**
- Tests RTL-SDR via rtl_test
- Detects specific error types
- Returns actionable error messages
- **Usage:** Pre-flight checks

#### **`test_frequency(...) -> Tuple[bool, str]`**
- Records 2-3 second test at target frequency
- Validates output WAV
- **Usage:** Verify frequency before scheduled pass

#### **`pre_recording_check(...) -> Dict[str, Any]`**
- Runs all pre-recording diagnostics
- Checks: RTL-SDR connection, disk space, frequency
- **Usage:** Validate setup before recording

#### **`check_disk_space(...) -> Tuple[bool, str]`**
- Checks for sufficient free space
- Cross-platform (uses shutil.disk_usage)
- **Usage:** Pre-flight check

---

## Integration Instructions

### Step 1: Apply sdr_diagnostics.py
Already created at: `app/utils/sdr_diagnostics.py`

### Step 2: Update sdr_scheduler.py

**Location:** `app/utils/sdr_scheduler.py`, function `record_pass()` (line 96-155)

**Changes:**
1. Add import:
   ```python
   from app.utils.sdr_diagnostics import log_recording_command, validate_wav_file
   ```

2. In `record_pass()`, BEFORE subprocess.run() (around line 132):
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
   ```

3. After subprocess.run() completes (around line 140):
   ```python
   # Validate WAV file
   validation = validate_wav_file(wav)
   if validation["valid"]:
       log_and_print("info", f"[{sat}] WAV validated: {validation['format']}, {validation['duration_s']}s", plog)
       size = validation["size_mb"]
   else:
       error = f"WAV validation failed: {validation['error']}"
       log_and_print("error", f"[{sat}] {error}", plog)
   ```

**See full patch in:** `SCHEDULER_PATCH.md`

### Step 3: Update Manual Recorder UI (Optional but Recommended)

**Location:** `app/features/diagnostics/routes.py` and template

**Changes:**
- Add `/recorder/preview` endpoint to show command
- Display command before execution
- Validate WAV after recording completes
- Show PPM readonly (sourced from calibration)

**See recommendations in:** `UI_ENHANCEMENTS.md`

---

## Key Improvements

| Issue | Before | After |
|-------|--------|-------|
| **Command visibility** | ❌ No logging | ✅ Full command logged with parameters before execution |
| **PPM tracking** | ❌ Loaded but not logged | ✅ Logged with each recording |
| **File validation** | ❌ Only size/existence checked | ✅ WAV header, format, duration verified |
| **Error messages** | ❌ Generic "command failed" | ✅ Specific WAV errors, RTL-SDR diagnostics |
| **RTL-SDR testing** | ❌ "Error 129" → unclear | ✅ "Permission denied - run sudo usermod..." |
| **Duration alignment** | ❌ Timeout could be too short | ✅ timeout = duration + 10 seconds |
| **UI feedback** | ❌ Silent failures | ✅ Command preview, validation feedback |

---

## Testing Checklist

### Immediate (No Code Changes Required)

- [ ] Test RTL-SDR connection: `python3 -m app.utils.sdr_diagnostics`
- [ ] Check permissions: `lsusb` (should show RTL device)
- [ ] Check PPM value: `cat settings.json | grep rtl_ppm`
- [ ] Manual test: Go to Diagnostics → Manual Recorder → Record 30s
- [ ] Check logs: `tail -f recordings/manual/*.txt`

### After Applying SCHEDULER_PATCH.md

- [ ] Enable recordings: UI → Recordings → Enable
- [ ] Wait for next ISS pass (or check "Passes" page)
- [ ] Check logs: `tail -f logs/scheduler.log`
- [ ] Verify command logged with PPM and frequency
- [ ] Verify WAV file created and validated
- [ ] Check metadata JSON for verdict

### Validation Tests

```bash
# Validate a WAV file
python3 << 'EOF'
from pathlib import Path
from app.utils.sdr_diagnostics import validate_wav_file
import json

result = validate_wav_file(Path('recordings/20251115_1430_ISS_145.800MHz.wav'))
print(json.dumps(result, indent=2))
EOF

# Test RTL-SDR
python3 << 'EOF'
from app.utils.sdr_diagnostics import verify_rtl_sdr_connection
connected, message = verify_rtl_sdr_connection()
print(f"Connected: {connected}\nMessage: {message}")
EOF

# Test disk space
python3 << 'EOF'
from pathlib import Path
from app.utils.sdr_diagnostics import check_disk_space
has_space, message = check_disk_space(Path('recordings'))
print(f"Has space: {has_space}\nMessage: {message}")
EOF
```

---

## Troubleshooting Guide

### Symptom: "No RTL-SDR Detected"
**Causes:**
- Device not connected
- Not in dialout group (permission issue)
- USB driver not installed

**Fix:**
```bash
# Check if device appears
lsusb | grep -i realtek

# Fix permissions
sudo usermod -a -G dialout $USER
# Then logout/login

# Install drivers if needed
sudo apt install rtl-sdr
```

### Symptom: "Error 129" or "USB Permission Denied"
**Cause:** User not in dialout group

**Fix:**
```bash
sudo usermod -a -G dialout $USER
# Logout and log back in
```

### Symptom: Empty or Invalid WAV Files
**Causes:**
- PPM too far off (frequency not tuned correctly)
- Gain too low or high
- Recording cut short (insufficient timeout)
- Disk full or I/O error

**Fix:**
1. Run calibration: Diagnostics → Calibrate SDR
2. Check PPM value: `cat settings.json`
3. Check disk space: `df -h`
4. Test frequency: Diagnostics → Manual Recorder (test 30s)
5. Check logs for command and any errors

### Symptom: "Recording Too Short" or Incomplete
**Cause:** Timeout too short or rtl_fm terminated early

**Fix:**
- Check: timeout should be `duration + 10` seconds
- Verify disk space before recording
- Check for system resource constraints

---

## Documentation Files Created

1. **`RECORDING_DEBUG.md`** - This file explains all issues and solutions
2. **`SCHEDULER_PATCH.md`** - Specific code changes needed for sdr_scheduler.py
3. **`UI_ENHANCEMENTS.md`** - Recommendations for manual recorder UI improvements
4. **`sdr_diagnostics.py`** - New diagnostic utility module (already created)

---

## Next Steps

### Priority 1 (Must Do)
1. Apply SCHEDULER_PATCH.md to sdr_scheduler.py
2. Test manual recording via Diagnostics → Manual Recorder
3. Verify logs show command and PPM
4. Enable recordings and check next pass

### Priority 2 (Should Do)
1. Add pre-recording checks to verify RTL-SDR and disk space
2. Update manual recorder UI with command preview
3. Add WAV validation feedback to UI

### Priority 3 (Nice to Have)
1. Add progress bar for long recordings
2. Add system health dashboard
3. Archive old recordings automatically

---

## Support

If recordings still fail after applying these changes:

1. **Check logs:** `tail -f logs/scheduler.log`
2. **Check pass log:** `cat recordings/{date}_{satellite}_{freq}.log`
3. **Validate RTL-SDR:** See Troubleshooting Guide above
4. **Manual test:** Diagnostics → Manual Recorder → 30s test
5. **Check PPM:** `cat settings.json | grep rtl_ppm`

The command will now be visible in the logs, making it much easier to diagnose issues!

---

**Status:** ✅ Diagnostics module created and documented  
**Action Required:** Apply SCHEDULER_PATCH.md to sdr_scheduler.py  
**Expected Result:** Full command visibility, PPM logging, and WAV file validation  
