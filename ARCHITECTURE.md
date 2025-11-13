# Recording Flow Diagram & Architecture

## Current Recording Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Web UI / Scheduler                                              │
│ Passes detected → ISS pass scheduled                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Enable Recordings (POST)
                         ▼
        ┌────────────────────────────────┐
        │ record_pass(sat, aos, los)     │
        │ app/utils/sdr_scheduler.py     │
        └────────────┬───────────────────┘
                     │
        ┌────────────▼──────────────────────────────────┐
        │ 1. Load PPM from settings.json                │
        │ 2. Set frequency, sample rate, gain           │
        │ 3. Calculate duration                         │
        └────────────┬──────────────────────────────────┘
                     │
                 [NEW] Log command & parameters
                     │
        ┌────────────▼──────────────────────────────────────┐
        │ 4. Execute command via subprocess.run()           │
        │    timeout {dur} rtl_fm -f {freq} -M fm ...     │
        │             | sox -t raw ... -c 1 {output}.wav  │
        │                                                  │
        │    RTL-SDR  →  Raw IQ  →  SOX  →  WAV File   │
        └────────────┬──────────────────────────────────────┘
                     │
                 [NEW] Validate WAV file
                     │
        ┌────────────▼──────────────────────────────────┐
        │ 5. Check:                                    │
        │    - Valid WAV header                        │
        │    - 16-bit mono 48000 Hz                   │
        │    - Duration >= expected                   │
        │    - File size > 1 KB                       │
        └────────────┬──────────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────────┐
        │ 6. Write metadata JSON                       │
        │    - Timestamp, frequency, duration          │
        │    - File size, verdict (PASS/FAIL)         │
        │    - Error message if any                    │
        └────────────┬──────────────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────┐
        │ Recordings directory         │
        │ - 20251115_1430_ISS.wav      │ ◄─── Validated
        │ - 20251115_1430_ISS.json     │ ◄─── Metadata
        │ - 20251115_1430_ISS.log      │ ◄─── Logs
        │ - 20251115_1430_ISS.png      │ ◄─── Spectrogram
        └─────────────────────────────┘
```

---

## Diagnostic Flow

```
┌────────────────────────────────────────────────┐
│ app/utils/sdr_diagnostics.py (NEW MODULE)      │
├────────────────────────────────────────────────┤
│                                                │
│ ┌──────────────────────────────────────────┐  │
│ │ validate_wav_file(path)                  │  │ ← Check file validity
│ │ Returns: {valid, format, duration, ...}  │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ ┌──────────────────────────────────────────┐  │
│ │ log_recording_command(...)               │  │ ← Log parameters
│ │ Prints formatted command box             │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ ┌──────────────────────────────────────────┐  │
│ │ verify_rtl_sdr_connection()              │  │ ← Test RTL-SDR
│ │ Returns: (connected, error_message)      │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ ┌──────────────────────────────────────────┐  │
│ │ test_frequency(freq, ppm)                │  │ ← Test recording
│ │ Returns: (success, result)               │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ ┌──────────────────────────────────────────┐  │
│ │ pre_recording_check(...)                 │  │ ← All checks
│ │ Returns: {ready, checks...}              │  │
│ └──────────────────────────────────────────┘  │
│                                                │
└────────────────────────────────────────────────┘
```

---

## Error Diagnosis Tree

```
Recording Fails
│
├─ File not created
│  ├─ RTL-SDR error?
│  │  ├─ "No devices found" → Check USB connection
│  │  ├─ "Permission denied" → sudo usermod -a -G dialout $USER
│  │  └─ "Error 129" → Same as above
│  │
│  ├─ Timeout too short?
│  │  └─ Increase: timeout should be duration + 10s
│  │
│  └─ Disk full?
│     └─ Check: df -h
│
├─ File created but invalid
│  ├─ Empty file (0 bytes)?
│  │  ├─ PPM wrong → Run calibration
│  │  └─ Frequency wrong → Check config
│  │
│  ├─ File too small?
│  │  └─ Recording cut short → Check timeout, disk space
│  │
│  ├─ Wrong format (not 16-bit mono)?
│  │  └─ sox format issue → Check sox command
│  │
│  └─ Duration mismatch?
│     └─ rtl_fm terminated early → Check USB, gain, frequency
│
└─ File valid but content issues
   ├─ No audio data?
   │  ├─ Gain too low → Try 40 dB
   │  ├─ Frequency wrong → Calibrate PPM
   │  └─ No signal at location → Check pass prediction
   │
   └─ Poor quality?
      ├─ PPM off by much → Calibrate
      └─ Gain wrong → Adjust 20-40 dB range
```

---

## Command Execution Flow (With Logging)

```
scheduler.record_pass()
│
├─ Load settings (PPM, etc)
│
├─ Calculate parameters:
│  ├─ frequency = 145.800 MHz = 145800000 Hz
│  ├─ ppm = 0 (from settings.json)
│  ├─ dur = 600s (pass duration + 30s margin)
│  └─ timeout = dur + 10 = 610s
│
├─ [NEW] log_recording_command()
│  └─ LOGS:
│      ======================================================================
│      [ISS] Recording Parameters:
│        Frequency:    145.800 MHz (145800000 Hz)
│        PPM Correction: 0 ppm
│        Sample Rate:  48000 Hz
│        Gain:         29.7 dB
│        Duration:     600 seconds (timeout: 610s)
│        Output:       recordings/20251115_1430_ISS_145.800MHz.wav
│      ──────────────────────────────────────────────────────────────────
│      Full Command:
│        timeout 610 rtl_fm -f 145,800,000 -M fm -s 48,000 -g 29.7 -l 0 -p 0 | sox -t raw -r 48,000 -e signed -b 16 -c 1 - -c 1 recordings/...
│      ======================================================================
│
├─ EXECUTE: subprocess.run(cmd, shell=True)
│  ├─ rtl_fm reads 145.800 MHz from RTL-SDR
│  ├─ Pipes raw IQ stream to sox
│  ├─ sox converts to 16-bit mono WAV
│  ├─ Writes to file (progress visible in system monitor)
│  └─ Exits when timeout expires or recording complete
│
├─ [NEW] validate_wav_file()
│  └─ CHECKS:
│      ├─ File exists? ✓
│      ├─ Valid WAV header? ✓
│      ├─ Format: 16-bit mono 48000 Hz? ✓
│      ├─ Duration: 623.5s (expected ~620s)? ✓
│      ├─ Size: 45.2 MB? ✓
│      └─ RESULT: valid=True
│
├─ [NEW] log_recording_command() output
│  └─ LOGS:
│      [ISS] WAV validated: 16-bit mono 48000 Hz, 623.5s
│
├─ Write metadata JSON
│  └─ {
│       "satellite": "ISS",
│       "frequency": 145.8,
│       "duration_s": 620,
│       "file_mb": 45.2,
│       "verdict": "PASS",
│       "error": null
│     }
│
└─ COMPLETE ✓
```

---

## Before/After Comparison

### Before (Opaque)
```
[ISS] ▶ WAV capture for 600s at 145.800 MHz
[ISS] PASS COMPLETE — FAIL — 0.00 MB
```
❌ Why did it fail? No visibility!

### After (Transparent)
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
✅ Clear visibility at every step!

---

## Validation State Machine

```
START
  │
  ├─ File exists?
  │  └─ No  → ERROR: "File does not exist"
  │  └─ Yes → Check header
  │
  ├─ Valid WAV header?
  │  └─ No  → ERROR: "Invalid WAV file: [reason]"
  │  └─ Yes → Check format
  │
  ├─ Format == 16-bit mono?
  │  └─ No  → ERROR: "Wrong format: [actual]"
  │  └─ Yes → Check duration
  │
  ├─ Duration > 0?
  │  └─ No  → ERROR: "Empty WAV file (0 duration)"
  │  └─ Yes → Check size
  │
  ├─ Size > 1 KB?
  │  └─ No  → ERROR: "File too small ([size])"
  │  └─ Yes → SUCCESS
  │
  └─ VALID ✓
     Return all metadata

STATE:
  {
    "valid": true,
    "format": "16-bit mono 48000 Hz",
    "duration_s": 623.5,
    "size_mb": 45.23,
    "frames": 29928000,
    "sample_rate": 48000,
    "channels": 1,
    "sample_width": 2,
    "error": null
  }
```

---

## Integration Points

```
┌──────────────────────────────────────┐
│ sdr_scheduler.py                     │
│ (imports sdr_diagnostics)            │
│                                      │
│ record_pass():                       │
│  ├─ log_recording_command()          │
│  └─ validate_wav_file()              │
└──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│ sdr_diagnostics.py (NEW)             │
│                                      │
│ ├─ validate_wav_file()               │
│ ├─ build_rtl_fm_command()            │
│ ├─ build_sox_command()               │
│ ├─ log_recording_command()           │
│ ├─ verify_rtl_sdr_connection()       │
│ ├─ test_frequency()                  │
│ ├─ check_disk_space()                │
│ └─ pre_recording_check()             │
└──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│ Used by:                             │
│ ├─ sdr_scheduler.py (recording)      │
│ ├─ diagnostics/routes.py (UI)        │
│ └─ CLI tools (testing)               │
└──────────────────────────────────────┘
```

---

## Key Metrics to Monitor

After implementing these changes, monitor:

1. **Command Visibility**: Every recording should log exact command BEFORE execution
2. **PPM Tracking**: PPM value visible in every recording log
3. **Success Rate**: Count of PASS vs FAIL verdicts
4. **File Quality**: All files validated (no empty/corrupt)
5. **Duration Accuracy**: Actual vs expected duration
6. **Error Clarity**: Can you understand why each failure occurred?

If all six show improvement, the diagnostics integration is working! ✓
