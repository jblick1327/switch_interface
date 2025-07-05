"""Windows WASAPI helpers.

`get_extra_settings()` returns `sd.WasapiSettings(exclusive=True)` when the
current host API's name is ``"Windows WASAPI"``. If the host API differs or
any error occurs, ``None`` is returned so callers can fall back to shared
mode gracefully.
"""

from __future__ import annotations

from typing import Optional

import sounddevice as sd


def get_extra_settings() -> Optional[sd.WasapiSettings]:
    """Return exclusive-mode settings for WASAPI if available."""
    try:
        info = sd.query_hostapis(sd.default.hostapi)
        if info.get("name") == "Windows WASAPI":
            return sd.WasapiSettings(exclusive=True)
    except Exception:
        pass
    return None
