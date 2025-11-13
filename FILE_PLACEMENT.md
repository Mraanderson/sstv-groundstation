# File Placement Guide

This guide shows where all documentation and code files belong in your project.

## 📁 Project Structure Overview

```
sstv-groundstation/
├── app/
│   ├── utils/
│   │   ├── sdr_diagnostics.py          ✅ NEW - already created
│   │   └── sdr_scheduler.py            ⚠️ PATCH - needs changes
│   └── features/
│       └── diagnostics/
│           ├── routes.py               ⚠️ PATCH - needs changes
│           └── templates/
│               └── diagnostics/
│                   └── manual_recorder.html  ⚠️ PATCH - needs changes
├── doc/
│   ├── features.md                     (existing)
│   ├── sdr_detection.md                (existing)
│   └── Todo.md                         (existing)
├── 📋 INDEX.md                         ✅ Documentation index
├── 📋 QUICK_START.md                   ✅ Implementation quick start
├── 📋 SCHEDULER_PATCH.md               ✅ Scheduler patch reference
├── 📋 RECORDING_FIX_SUMMARY.md         ✅ Root cause summary
├── 📋 RECORDING_DEBUG.md               ✅ Troubleshooting guide
├── 📋 ARCHITECTURE.md                  ✅ Architecture & flow diagrams
├── 📋 UI_ENHANCEMENTS.md               ✅ UI changes reference
├── 📋 DELIVERY.md                      ✅ Implementation summary
├── 📋 APPLY_PATCH.md                   ✅ Step-by-step patch guide
├── 📋 ENHANCED_ROUTES.md               ✅ New Flask routes
├── 📋 ENHANCED_HTML.md                 ✅ New HTML template
└── 📋 FILE_PLACEMENT.md                ✅ This file
```

## 🔧 Code Changes Required

### 1. **`app/utils/sdr_diagnostics.py`** (NEW FILE)
- **Status:** ✅ Already created and ready to use
- **Location:** `/app/utils/sdr_diagnostics.py`
- **No action needed** - File is already in place

### 2. **`app/utils/sdr_scheduler.py`** (PATCH REQUIRED)
- **Status:** ⚠️ Needs 3-section patch applied
- **Location:** `/app/utils/sdr_scheduler.py`
- **Apply from:** `APPLY_PATCH.md` (3 copy/paste sections)
- **Lines affected:** 7 (import), 132 (logging), 140-150 (validation)
- **Estimated time:** 5 minutes

### 3. **`app/features/diagnostics/routes.py`** (PATCH REQUIRED)
- **Status:** ⚠️ Needs route enhancements
- **Location:** `/app/features/diagnostics/routes.py`
- **Apply from:** `ENHANCED_ROUTES.md`
- **Changes:** Add 2 new routes + enhance manual_recorder handler
- **Estimated time:** 10 minutes

### 4. **`app/features/diagnostics/templates/diagnostics/manual_recorder.html`** (PATCH REQUIRED)
- **Status:** ⚠️ Needs complete HTML replacement
- **Location:** `/app/features/diagnostics/templates/diagnostics/manual_recorder.html`
- **Apply from:** `ENHANCED_HTML.md` (full template)
- **Changes:** Replace entire file with enhanced version
- **Estimated time:** 5 minutes

## 📚 Documentation Files

All `.md` files should be placed in the **project root** (`/sstv-groundstation/`)

| File | Purpose | Size | Priority |
|------|---------|------|----------|
| `INDEX.md` | Central documentation hub | 1-2 KB | HIGH |
| `QUICK_START.md` | 5-minute implementation guide | 3-4 KB | HIGH |
| `APPLY_PATCH.md` | Copy/paste scheduler patch | 5-6 KB | HIGH |
| `ENHANCED_ROUTES.md` | New Flask routes code | 4-5 KB | HIGH |
| `ENHANCED_HTML.md` | New HTML template code | 6-7 KB | HIGH |
| `SCHEDULER_PATCH.md` | Patch reference docs | 3-4 KB | MEDIUM |
| `RECORDING_FIX_SUMMARY.md` | Root cause analysis | 4-5 KB | MEDIUM |
| `RECORDING_DEBUG.md` | Troubleshooting guide | 5-6 KB | MEDIUM |
| `ARCHITECTURE.md` | Architecture & diagrams | 6-7 KB | MEDIUM |
| `UI_ENHANCEMENTS.md` | UI features reference | 3-4 KB | MEDIUM |
| `DELIVERY.md` | Implementation summary | 2-3 KB | LOW |
| `FILE_PLACEMENT.md` | This file | 3-4 KB | REFERENCE |

## ✅ Implementation Checklist

Follow this order for smooth implementation:

### Phase 1: Preparation (5 min)
- [ ] Read `QUICK_START.md` for overview
- [ ] Backup current code files
- [ ] Create `doc/DIAGNOSTICS_README.md` (optional - stores doc links)

### Phase 2: Code Changes (20 min)

#### Step 1: Patch `sdr_scheduler.py` (5 min)
```
1. Open: app/utils/sdr_scheduler.py
2. Apply patches from: APPLY_PATCH.md
   - Section 1: Add import (line 7)
   - Section 2: Add logging (line 132)
   - Section 3: Add validation (line 140-150)
3. Save file
4. Result: Full command logged, WAV validated
```

#### Step 2: Update `diagnostics/routes.py` (10 min)
```
1. Open: app/features/diagnostics/routes.py
2. Add new routes from: ENHANCED_ROUTES.md
   - New: recorder/preview endpoint
   - New: recorder/status endpoint
   - Enhance: manual_recorder POST handler
3. Save file
4. Result: Preview & status endpoints available
```

#### Step 3: Replace HTML template (5 min)
```
1. Open: app/features/diagnostics/templates/diagnostics/manual_recorder.html
2. Replace entire file with: ENHANCED_HTML.md
3. Save file
4. Result: Enhanced UI with command preview & validation
```

### Phase 3: Testing (10 min)
- [ ] Start Flask app
- [ ] Navigate to Manual Recorder page
- [ ] Click "Preview Command" button
- [ ] Verify command shows correct frequency, PPM, duration
- [ ] Click "Start Recording" and verify logs show command
- [ ] Check log files for full command output

### Phase 4: Verification (5 min)
- [ ] ✅ Command preview displays correctly
- [ ] ✅ PPM value shown in preview
- [ ] ✅ Full command logged before execution
- [ ] ✅ WAV validation runs after recording
- [ ] ✅ Status shows validation results

## 📂 Documentation Organization

### For Quick Reference
Keep these 3 files bookmarked:
1. `QUICK_START.md` - How to implement
2. `APPLY_PATCH.md` - Copy/paste patches
3. `ENHANCED_ROUTES.md` - Route code

### For Understanding
Read these for deep dives:
1. `RECORDING_FIX_SUMMARY.md` - What was wrong
2. `ARCHITECTURE.md` - How it works
3. `RECORDING_DEBUG.md` - Troubleshooting

### For Reference
Keep available for later:
1. `INDEX.md` - Navigation hub
2. `UI_ENHANCEMENTS.md` - Feature reference
3. `DELIVERY.md` - Implementation notes

## 🚀 Implementation Order

**DO NOT:** Apply patches in random order
**DO:** Follow this sequence:

1. **First:** `sdr_scheduler.py` (enables diagnostics)
2. **Second:** `diagnostics/routes.py` (endpoints)
3. **Third:** `manual_recorder.html` (UI)

> Each step depends on the previous one

## 📋 File Sizes & Line Counts

| File | Lines | Size | Time to Apply |
|------|-------|------|----------------|
| sdr_diagnostics.py | 400+ | 12 KB | 0 min (pre-made) |
| sdr_scheduler.py (patch) | 30+ | 1 KB patch | 5 min |
| diagnostics/routes.py (patch) | 40+ | 1.5 KB patch | 10 min |
| manual_recorder.html (full) | 150+ | 6 KB | 5 min |
| Total code time | ~70 new lines | 20 KB | 20 min |

## 🔍 Verification Checklist

After implementing all patches, verify:

### Command Logging
```
✅ Scheduler logs show full rtl_fm command
✅ PPM value is visible in logs
✅ Frequency/Duration/Bandwidth logged
✅ sox command includes WAV conversion
```

### WAV Validation
```
✅ After recording, validation runs
✅ Format checked (PCM, 16-bit mono)
✅ Duration logged and compared to target
✅ File size reasonable for duration
✅ Errors reported if file invalid
```

### UI Enhancements
```
✅ Preview Command button works
✅ Command shows full text in preview box
✅ Status button returns validation results
✅ Recent files listed in table
✅ Tips section visible
```

### Error Handling
```
✅ Missing PPM handled gracefully
✅ Invalid frequency rejected with message
✅ RTL-SDR errors clearly identified
✅ Disk space issues detected
```

## 📞 Support Reference

If you get stuck:

1. **Command not logging?** → See APPLY_PATCH.md Section 2
2. **Preview endpoint 404?** → See ENHANCED_ROUTES.md Section 1
3. **HTML not rendering?** → See ENHANCED_HTML.md Integration Steps
4. **Validation fails?** → See RECORDING_DEBUG.md Troubleshooting
5. **General flow confused?** → See ARCHITECTURE.md Diagrams

## 📝 Notes

- All `.md` files are documentation only - they don't need to be in any specific location
- The only files that matter for functionality are the Python code changes
- Backup originals before editing
- All changes are backward compatible
- No new dependencies required

## 🎯 Expected Outcome

After completing all steps:

```
✅ Full command logged before every recording
✅ PPM correction value displayed in logs
✅ WAV file validated after recording
✅ UI shows command preview with copy button
✅ Status endpoint shows validation results
✅ Error messages clearly identify issues
✅ Complete ISS pass recordings work properly
```

---

**Start here:** Read `QUICK_START.md`, then begin with `APPLY_PATCH.md`

