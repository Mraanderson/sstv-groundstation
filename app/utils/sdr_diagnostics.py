"""
sdr_diagnostics.py — Diagnostic utilities for SDR recording validation and visibility.

This module provides functions to:
- Validate WAV file integrity (headers, format, duration)
- Log detailed recording commands for debugging
- Pre-verify PPM and frequency before recording
"""

import subprocess
import wave
import json
import logging
import os
from pathlib import Path
from typing import Dict, Tuple, Optional, Any

logger = logging.getLogger(__name__)


def validate_wav_file(wav_path: Path) -> Dict[str, Any]:
    """
    Validate a WAV file's integrity. Returns dict with detailed info or error.
    
    Returns:
        {
            "valid": bool,
            "error": str or None,
            "format": str (e.g., "16-bit mono 48000 Hz"),
            "duration_s": float,
            "size_mb": float,
            "frames": int,
            "sample_rate": int,
            "channels": int,
            "sample_width": int
        }
    """
    result = {
        "valid": False,
        "error": None,
        "format": None,
        "duration_s": 0.0,
        "size_mb": 0.0,
        "frames": 0,
        "sample_rate": 0,
        "channels": 0,
        "sample_width": 0
    }
    
    if not wav_path.exists():
        result["error"] = f"File does not exist: {wav_path}"
        return result
    
    try:
        result["size_mb"] = round(wav_path.stat().st_size / (1024 * 1024), 2)
        
        with wave.open(str(wav_path), "rb") as w:
            result["channels"] = w.getnchannels()
            result["sample_width"] = w.getsampwidth()
            result["sample_rate"] = w.getframerate()
            result["frames"] = w.getnframes()
            result["duration_s"] = round(result["frames"] / result["sample_rate"], 2)
            
            # Validate basic constraints
            if result["duration_s"] == 0:
                result["error"] = "Empty WAV file (0 duration)"
                return result
            
            if result["size_mb"] < 0.001:  # < 1 KB
                result["error"] = f"File too small ({result['size_mb']} MB)"
                return result
            
            # Build format string
            bit_depth = result["sample_width"] * 8
            channel_str = "mono" if result["channels"] == 1 else f"{result['channels']}-ch"
            result["format"] = f"{bit_depth}-bit {channel_str} {result['sample_rate']} Hz"
            result["valid"] = True
            
    except wave.Error as e:
        result["error"] = f"Invalid WAV file: {e}"
    except Exception as e:
        result["error"] = f"Error reading WAV: {e}"
    
    return result


def build_rtl_fm_command(
    frequency_hz: int,
    ppm: int,
    sample_rate: int = 48000,
    gain: float = 29.7,
    duration_s: int = 30
) -> str:
    """
    Build a complete rtl_fm command with all parameters visible for logging.
    
    Args:
        frequency_hz: Frequency in Hz (e.g., 145800000 for 145.8 MHz)
        ppm: PPM correction factor
        sample_rate: Output sample rate (Hz)
        gain: RTL-SDR gain in dB
        duration_s: Duration of recording in seconds
    
    Returns:
        Complete rtl_fm command string
    """
    return (
        f"rtl_fm "
        f"-f {frequency_hz:,} "
        f"-M fm "
        f"-s {sample_rate:,} "
        f"-g {gain} "
        f"-l 0 "
        f"-p {ppm}"
    )


def build_sox_command(
    sample_rate: int = 48000,
    output_file: str = "output.wav"
) -> str:
    """
    Build a complete sox command for converting raw audio to WAV.
    
    Args:
        sample_rate: Input sample rate (Hz)
        output_file: Path to output WAV file
    
    Returns:
        sox command string (to be piped from rtl_fm)
    """
    return (
        f"sox "
        f"-t raw "
        f"-r {sample_rate:,} "
        f"-e signed "
        f"-b 16 "
        f"-c 1 "
        f"- "
        f"-c 1 "
        f"{output_file}"
    )


def log_recording_command(
    satellite: str,
    frequency_hz: int,
    frequency_mhz: float,
    ppm: int,
    duration_s: int,
    sample_rate: int,
    gain: float,
    output_wav: str,
    logger_obj: Optional[logging.Logger] = None
) -> str:
    """
    Log a detailed recording command for debugging. Returns formatted command string.
    
    Args:
        satellite: Satellite name (e.g., "ISS")
        frequency_hz: Frequency in Hz
        frequency_mhz: Frequency in MHz (for display)
        ppm: PPM correction
        duration_s: Duration in seconds
        sample_rate: Sample rate in Hz
        gain: Receiver gain
        output_wav: Output file path
        logger_obj: Optional logger object; if None, uses module logger
    
    Returns:
        Formatted command string
    """
    log = logger_obj or logger
    
    rtl_fm_cmd = build_rtl_fm_command(frequency_hz, ppm, sample_rate, gain)
    sox_cmd = build_sox_command(sample_rate, output_wav)
    full_cmd = f"timeout {duration_s + 10} {rtl_fm_cmd} | {sox_cmd}"
    
    msg = (
        f"\n{'='*70}\n"
        f"[{satellite}] Recording Parameters:\n"
        f"  Frequency:    {frequency_mhz:.3f} MHz ({frequency_hz:,} Hz)\n"
        f"  PPM Correction: {ppm} ppm\n"
        f"  Sample Rate:  {sample_rate:,} Hz\n"
        f"  Gain:         {gain} dB\n"
        f"  Duration:     {duration_s} seconds (timeout: {duration_s + 10}s)\n"
        f"  Output:       {output_wav}\n"
        f"─" * 70 + "\n"
        f"Full Command:\n"
        f"  {full_cmd}\n"
        f"{'='*70}\n"
    )
    log.info(msg)
    return full_cmd


def verify_rtl_sdr_connection(timeout_s: int = 3) -> Tuple[bool, str]:
    """
    Test RTL-SDR connection via rtl_test. Returns (success, message).
    
    Returns:
        (is_connected: bool, message: str with error details if failed)
    """
    try:
        result = subprocess.run(
            ["rtl_test", "-t"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            text=True
        )
        
        output = (result.stdout or "") + (result.stderr or "")
        
        # rtl_test returns 0 on success
        if result.returncode == 0:
            return True, "RTL-SDR connected and responding"
        
        # Check for common error messages
        if "No devices found" in output:
            return False, "❌ No RTL-SDR devices found. Check USB connection."
        elif "Permission denied" in output or "LIBUSB_ERROR_ACCESS" in output:
            return False, "❌ Permission denied. Try: sudo usermod -a -G dialout $USER"
        elif "timeout" in output.lower():
            return False, "❌ Device timeout. Check USB connection and drivers."
        elif "129" in output or "LIBUSB_ERROR" in output:
            return False, f"❌ USB Error {result.returncode} in output: {output[:100]}"
        else:
            return False, f"❌ rtl_test failed with code {result.returncode}: {output[:100]}"
    
    except subprocess.TimeoutExpired:
        return False, "❌ rtl_test timed out (device not responding)"
    except FileNotFoundError:
        return False, "❌ rtl_test not found. Install RTL-SDR tools: sudo apt install rtl-sdr"
    except Exception as e:
        return False, f"❌ Error testing RTL-SDR: {e}"


def test_frequency(
    frequency_hz: int,
    ppm: int = 0,
    duration_s: int = 3,
    sample_rate: int = 48000
) -> Tuple[bool, str]:
    """
    Quick test: Record a short sample at a frequency to verify RTL-SDR + frequency.
    
    Returns:
        (success: bool, message: str)
    """
    test_file = Path("/tmp/rtl_test_freq.wav")
    
    try:
        # Build and run command
        cmd = (
            f"timeout {duration_s + 5} rtl_fm "
            f"-f {frequency_hz} -M fm -s {sample_rate} -g 29.7 -l 0 -p {ppm} "
            f"| sox -t raw -r {sample_rate} -e signed -b 16 -c 1 - {test_file}"
        )
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if not test_file.exists():
            return False, f"Test recording failed: file not created. stderr: {result.stderr[:100]}"
        
        # Validate the recording
        validation = validate_wav_file(test_file)
        test_file.unlink()  # Clean up
        
        if not validation["valid"]:
            return False, f"Invalid test WAV: {validation['error']}"
        
        if validation["duration_s"] < 1:
            return False, f"Test recording too short ({validation['duration_s']}s)"
        
        return True, f"✅ Frequency test OK: {validation['format']}, {validation['duration_s']}s recorded"
    
    except Exception as e:
        if test_file.exists():
            test_file.unlink()
        return False, f"Frequency test failed: {e}"


def check_disk_space(path: Path, min_gb: float = 3.0) -> Tuple[bool, str]:
    """
    Check if path has sufficient free disk space.
    
    Returns:
        (has_space: bool, message: str)
    """
    try:
        check_path = path if path.is_dir() else path.parent
        # Use shutil.disk_usage for cross-platform compatibility
        import shutil
        total, used, free = shutil.disk_usage(str(check_path))
        free_gb = free / (1024 ** 3)
        
        if free_gb >= min_gb:
            return True, f"✅ {free_gb:.1f} GB free (need {min_gb} GB)"
        else:
            return False, f"❌ Only {free_gb:.1f} GB free (need {min_gb} GB)"
    except Exception as e:
        return False, f"❌ Could not check disk space: {e}"


def pre_recording_check(
    satellite: str,
    frequency_hz: int,
    ppm: int,
    output_dir: Path,
    sample_rate: int = 48000
) -> Dict[str, Any]:
    """
    Run all pre-recording diagnostics. Returns results dict.
    
    Returns:
        {
            "ready": bool,
            "rtl_sdr": (is_connected, message),
            "disk_space": (has_space, message),
            "frequency_test": (success, message)  # optional, only if RTL-SDR connected
        }
    """
    checks = {
        "ready": False,
        "rtl_sdr": verify_rtl_sdr_connection(),
        "disk_space": check_disk_space(output_dir)
    }
    
    # Only test frequency if RTL-SDR is working
    if checks["rtl_sdr"][0]:
        checks["frequency_test"] = test_frequency(frequency_hz, ppm, duration_s=2, sample_rate=sample_rate)
    
    checks["ready"] = all(
        result[0] for result in checks.values()
        if isinstance(result, tuple)
    )
    
    return checks


if __name__ == "__main__":
    # Test the diagnostic functions
    logging.basicConfig(level=logging.INFO)
    
    # Example: Check RTL-SDR connection
    connected, msg = verify_rtl_sdr_connection()
    print(f"RTL-SDR: {msg}")
    
    # Example: Check disk space
    has_space, msg = check_disk_space(Path("recordings"))
    print(f"Disk: {msg}")
    
    # Example: Log a command
    log_recording_command(
        satellite="ISS",
        frequency_hz=145_800_000,
        frequency_mhz=145.800,
        ppm=0,
        duration_s=600,
        sample_rate=48000,
        gain=29.7,
        output_wav="recordings/test.wav"
    )

