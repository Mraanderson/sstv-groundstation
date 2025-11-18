# PATCH APPLICATION GUIDE - COPY/PASTE READY

## Apply These Changes to `app/utils/sdr_scheduler.py`

---

```

**KEY CHANGES:**
- `timeout {dur}` → `timeout {dur+10}` (extended timeout)
- Added `log_recording_command()` call before subprocess
- Added WAV validation after subprocess
- Fixed sox command: `f" -c 1 {wav}"` → `f"-c 1 {wav}"` (removed extra space)

---

### CHANGE 3: Enhanced Error Logging (Line ~145-150, error handling)

**FIND THIS:**
```python
    except Exception as e:
        error = str(e)

    verdict = "PASS" if not error and size > 0 else "FAIL"
    #...
    print(f"{GREEN if verdict=='PASS' else RED}[{sat}] PASS COMPLETE — {verdict} — {size:.2f} MB{RESET}")
```

**REPLACE WITH:**
```python
    except Exception as e:
        error = str(e)
        log_and_print("error", f"[{sat}] Recording failed: {error}", plog)

    verdict = "PASS" if not error and size > 0 else "FAIL"
    log_and_print("info", f"[{sat}] RESULT: {verdict} | Size: {size:.2f}MB | Error: {error or 'None'}", plog)
    print(f"{GREEN if verdict=='PASS' else RED}[{sat}] PASS COMPLETE — {verdict} — {size:.2f} MB{RESET}")
```

---

## Summary of Changes

| Line | Change | Reason |
|------|--------|--------|
| 7 | Add import `sdr_diagnostics` | Enable diagnostics functions |
| 132 | Add `log_recording_command()` | Log all parameters before execution |
| 140 | Change `dur` to `dur+10` | Allow proper startup/shutdown |
| 143 | Add WAV validation | Check file integrity after recording |
| 150 | Enhanced error logging | Better error visibility |

**Total Changes:** 3 sections, ~30 lines added

**Time to Apply:** 5 minutes

---

## Testing After Patching

```bash
# 1. Restart Flask server
# (assuming you're running from /sstv-groundstation)
# Ctrl+C to stop, then:
python run.py

# 2. Test Manual Recorder
# Go to: http://localhost:5000/diagnostics
# Diagnostics → Manual Recorder
# Click "Record" (30 seconds)

# 3. Check logs
tail -f recordings/manual/*.txt

# Should see:
# ======================================================================
# [Manual] Recording Parameters:
#   Frequency:    145.800 MHz
#   PPM Correction: 0 ppm
#   Duration:     30 seconds
#   ...
# ======================================================================
```

---

## Verification

After applying the patch, you should see:

✅ Command box logged with full parameters  
✅ PPM value visible in logs  
✅ WAV validation result after recording  
✅ No errors during execution  

If you get `ModuleNotFoundError: sdr_diagnostics`, make sure `app/utils/sdr_diagnostics.py` exists.



