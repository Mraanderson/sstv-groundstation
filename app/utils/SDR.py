"""
sdr.py — RTL-SDR detection utilities
"""

import subprocess


def rtl_sdr_present() -> bool:
    """
    Check if an RTL-SDR device is connected and accessible.

    Returns:
        bool: True if an RTL-SDR is detected and responding, False otherwise.
    """
    try:
        # 'rtl_test -t' exits with 0 if it can talk to a dongle
        result = subprocess.run(
            ["rtl_test", "-t"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        return result.returncode == 0
    except FileNotFoundError:
        # rtl_test not installed or not in PATH
        return False
    except subprocess.SubprocessError:
        # Any other error (timeout, etc.)
        return False


if __name__ == "__main__":
    # Simple CLI test
    if rtl_sdr_present():
        print("✅ RTL-SDR detected and ready.")
    else:
        print("❌ No RTL-SDR detected.")
