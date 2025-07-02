"""detection.py – AbleNet press detector (**falling‑edge** algorithm)
====================================================================
Detect **one event per physical press** by spotting the characteristic *falling
edge* that appears at the start of every switch hit (circled in the screenshots
you shared).

Why change?
-----------
Your scope traces show a stable pattern:
    small +ve bump  →  sharp drop to about −0.8 ... −1.0
The release, a second or so later, is just the inverse (−ve → +ve) and often
oscillates; ignoring that edge entirely eliminates both early and delayed
false triggers.

Algorithm
~~~~~~~~~
* Maintain a tiny 1‑sample history per channel.
* When *armed*:
    if **prev ≥ UPPER_THRESHOLD** **and** **curr ≤ LOWER_THRESHOLD** → fire
      • call ``on_press`` once
      • start a cooldown (debounce) timer so bounces in the same press are ignored
* When *cooling‑down*: decrement a sample counter; re‑arm when it hits 0.

Key constants (tweak these during calibration)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
UPPER_THRESHOLD ... near  0.0 (e.g. −0.10)
LOWER_THRESHOLD ... near −0.3 … −0.5  (e.g. −0.35)
DEBOUNCE_MS ...... 20 – 50 ms  (converted to samples)
BLOCKSIZE ........ 256 (≈ 6 ms @ 44.1 kHz)

The detector never measures RMS or noise floor; the GUI calibrator will pick
UPPER/LOWER once and store them.
"""
from __future__ import annotations

import math
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

# ---------------------------------------------------------------------------
# User‑facing helper
# ---------------------------------------------------------------------------

def listen(
    on_press: Callable[[], None],
    *,
    upper_threshold: float = -0.10,
    lower_threshold: float = -0.35,
    samplerate: int = 44_100,
    blocksize: int = 256,
    debounce_ms: int = 20,
    device: Optional[int | str] = None,
) -> None:
    """Start listening on *device* (defaults to system default input).

    The function **blocks**.  Press *Ctrl‑C* to exit.

    Parameters
    ----------
    on_press
        Callback executed *once* per detected press (runs in audio thread – keep it fast!).
    upper_threshold, lower_threshold
        Dual signed thresholds that define a *falling edge* (prev ≥ upper, curr ≤ lower).
    samplerate, blocksize
        Audio stream parameters.  Smaller *blocksize* catches shorter spikes.
    debounce_ms
        Minimum time between successive press events.
    device
        PortAudio device index or name string.  *None → default*.
    """
    if upper_threshold <= lower_threshold:
        raise ValueError("upper_threshold must be > lower_threshold (both negative values)")

    refractory_samples = int(math.ceil((debounce_ms / 1_000) * samplerate))

    state = _EdgeState(armed=True, cooldown=0)

    def _callback(indata: np.ndarray, frames: int, _: int, __: int):
        nonlocal state
        # Flatten to mono – take max magnitude across channels to be safe.
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]

        prev = state.prev_sample
        for sample in mono:
            if state.armed:
                if prev >= upper_threshold and sample <= lower_threshold:
                    on_press()
                    state.armed = False
                    state.cooldown = refractory_samples
            else:
                state.cooldown -= 1
                if state.cooldown <= 0:
                    state.armed = True
            prev = sample
        state.prev_sample = prev

    with sd.InputStream(
        samplerate=samplerate,
        blocksize=blocksize,
        channels=1,
        dtype="float32",
        callback=_callback,
        device=device,
    ):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            return


@dataclass
class _EdgeState:
    armed: bool
    cooldown: int
    prev_sample: float = 0.0


# ---------------------------------------------------------------------------
# Quick‑start harness
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 🔧 Edit these four numbers while tinkering in VS Code.
    UPPER_THRESHOLD = -0.3   # prev sample must be ≥ this (closer to 0)
    LOWER_THRESHOLD = -0.7   # current sample must drop below this
    BLOCKSIZE       = 256     # 6 ms @ 44.1 kHz – good for short spikes
    DEBOUNCE_MS     = 85

    import datetime as _dt

    def _on_press():
        ts = _dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"{ts}  PRESS")

    print("Listening…  (Ctrl‑C to stop)")
    listen(
        _on_press,
        upper_threshold=UPPER_THRESHOLD,
        lower_threshold=LOWER_THRESHOLD,
        blocksize=BLOCKSIZE,
        debounce_ms=DEBOUNCE_MS,
    )
