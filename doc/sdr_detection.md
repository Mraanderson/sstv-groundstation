# SDR Detection and Handling

## Scenarios

- Software installed but no SDR dongle connected
- Dongle connected but in use by other software
- Dongle in use by this project
- SDR present but software missing (rtl_test utility not installed)

## Solution for End User

1. Detect if the rtl_test utility is installed; if not, inform the user to install it.
2. Check if the RTL-SDR dongle is connected and accessible.
3. If the dongle is not detected, provide clear user-friendly messages explaining possible reasons:
   - Dongle not connected
   - Dongle in use by another application
   - Permission issues
4. Offer options to the user:
   - Retry detection
   - Run in a limited or mock mode (if applicable)
   - Exit with instructions on how to resolve the issue
5. Log detailed error information for troubleshooting.
6. Optionally, provide a diagnostic command or script to help users identify issues.
