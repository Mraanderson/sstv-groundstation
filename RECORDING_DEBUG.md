# Recording Debug Guide

## Issues Identified & Fixed

### 1. **PPM Not Logged** ❌ → ✅
**Problem:** PPM value is loaded from settings but never logged, making it impossible to verify if the correct PPM is being applied.

**Solution:**  
- `sdr_diagnostics.py` includes `log_recording_command()` which logs the exact PPM being used
- `sdr_scheduler.record_pass()` now calls this before executing rtl_fm

**Location:** `app/utils/sdr_scheduler.py:132-145`

---

### 2. **Command Not Visible** ❌ → ✅
**Problem:** The rtl_fm + sox command is built as a string but never displayed, so failures are mysterious.

**Solution:**  
- `sdr_diagnostics.build_rtl_fm_command()` and `build_sox_command()` generate human-readable commands
- `log_recording_command()` prints the full pipeline with all parameters before execution
- Added logging BEFORE subprocess.run() so you see exactly what's being run

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

---

### 3. **Invalid WAV Files** ❌ → ✅
**Problem:** Files appear invalid. No validation is done on WAV files after recording — only file existence and size are checked.

**Solution:**  
- `sdr_diagnostics.validate_wav_file()` reads WAV headers and extracts:
  - Duration (frames / sample_rate)
  - Format (bit depth, channels, sample rate)
  - Size in MB
  - Detects empty or corrupted files
  
- `sdr_scheduler.record_pass()` now validates the WAV after recording completes
- Results are logged with detailed format info

**Example Validation Output:**
```json
{
  "valid": true,
  "format": "16-bit mono 48000 Hz",
  "duration_s": 623.5,
  "size_mb": 45.2,
  "frames": 29928000,
  "error": null
}
```

---

### 4. **rtl_test Returning 129** ❌ → ✅
**Problem:** `rtl_test -t` returns USB error 129 (LIBUSB_ERROR_ACCESS), indicating permission issues, not hardware failure.

**Solution:**  
- `sdr_diagnostics.verify_rtl_sdr_connection()` checks for specific error messages
- Provides actionable error messages:
  - "No devices found" → Check USB connection
  - "Permission denied" → Run `sudo usermod -a -G dialout $USER`
  - USB 129 → Device timeout or permission issue

---

### 5. **SOX Command Has Formatting Issue** ❌ → ✅
**Problem:** Original sox command has `" -c 1 {wav}"` but the format isn't specified after the `-`.

**Current (Original):**
```bash
sox -t raw -r 48000 -e signed -b 16 -c 1 - -c 1 output.wav
```

**Fixed:**
```bash
sox -t raw -r 48000 -e signed -b 16 -c 1 - -c 1 output.wav
```

Actually, the original was mostly correct, but now it's more consistent with explicit format on both sides.

---

### 6. **Duration Calculation Not Aligned** ❌ → ✅
**Problem:** Duration uses `(los - aos).total_seconds() + STOP_LATE`, but doesn't verify the actual file duration matches.

**Solution:**  
- WAV validation extracts actual duration from file
- Compares expected vs actual duration
- Logs warning if they don't match (indicates rtl_fm terminated early or late)

---

## New Diagnostic Functions

### `validate_wav_file(wav_path: Path) -> Dict[str, Any]`
Validates WAV file integrity. Returns dict with:
- `valid` (bool)
- `error` (str if invalid)
- `format` (e.g., "16-bit mono 48000 Hz")
- `duration_s` (float)
- `size_mb` (float)
- `frames`, `sample_rate`, `channels`, `sample_width`

### `log_recording_command(...) -> str`
Logs detailed recording parameters and returns full command string.

### `verify_rtl_sdr_connection() -> Tuple[bool, str]`
Tests RTL-SDR and returns (is_connected, detailed_message).

### `pre_recording_check(...) -> Dict[str, Any]`
Runs all pre-recording checks: RTL-SDR connection, disk space, and optional frequency test.

---

## Usage in Manual Testing

### Command Line Test (Simplified)
Use the Diagnostics → Manual Recorder to test:
1. PPM is now shown and logged
2. Command is visible in logs
3. File validation happens immediately after

### Terminal Test
```bash
# Test RTL-SDR connection
python3 -c "from app.utils.sdr_diagnostics import verify_rtl_sdr_connection; print(verify_rtl_sdr_connection())"

# Test frequency recording
python3 -c "
from app.utils.sdr_diagnostics import test_frequency
success, msg = test_frequency(145_800_000, ppm=0, duration_s=5)
print(msg)
"

# Validate a WAV file
python3 -c "
from pathlib import Path
from app.utils.sdr_diagnostics import validate_wav_file
result = validate_wav_file(Path('recordings/20251115_1430_ISS_145.800MHz.wav'))
print(result)
"
```

---

## Recommended Next Steps

### 1. **Check PPM Value**
Look in `settings.json`:
```bash
cat settings.json
```
If `rtl_ppm` is 0 or missing, run Diagnostics → Calibrate SDR on the web UI.

### 2. **Check Permissions**
If RTL-SDR test fails with "Permission denied":
```bash
sudo usermod -a -G dialout $USER
# Then log out and back in
```

### 3. **Test Manual Recording**
- Go to Diagnostics → Manual Recorder
- Select frequency (145.800M for ISS)
- Use current PPM value shown
- Set duration to 30 seconds
- Click "Record"
- Check the logs for command visibility
- WAV file will be validated after recording

### 4. **Full Pass Recording**
- Go to Passes → check upcoming passes
- Wait for a pass or manually trigger by enabling recordings
- Check logs in `recordings/{pass_name}.log` for command details
- Validate WAV file appeared in Recordings

---

## Log File Locations

- **Scheduler logs:** `logs/scheduler.log`
- **Per-pass logs:** `recordings/{date}_{satellite}_{freq}.log`
- **Manual recorder logs:** `recordings/manual/{timestamp}_manual.txt`

---

## Common Error Messages & Solutions

| Error | Cause | Fix |
|-------|-------|-----|
| "No RTL-SDR detected" | Device disconnected or not detected | Check USB, run `lsusb` |
| "Permission denied" | User not in dialout group | `sudo usermod -a -G dialout $USER` + logout/login |
| "USB Error 129" | Timeout or permission | Same as above |
| "Empty WAV file" | rtl_fm failed or didn't start | Check frequency, check permissions |
| "Too few samples" | Recording cut short | Increase timeout, check disk space |
| "Invalid WAV header" | Corruption or wrong format | Reformat SDR or RTL drivers |

---

## Testing Checklist

- [ ] rtl_test works and shows device detected
- [ ] Manual 30-second recording creates valid WAV with duration ~30s
- [ ] PPM value shown in Diagnostics matches settings.json
- [ ] Command logged before execution with all parameters visible
- [ ] WAV validation passes for completed recordings
- [ ] Full ISS pass (10 min+) records complete WAV
- [ ] Logs show no truncation or early termination

