from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

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

if __name__ == "__main__":
    UPPER_THRESHOLD = -0.2
    LOWER_THRESHOLD = -0.5   # current sample must drop below this
    BLOCKSIZE       = 256
    DEBOUNCE_MS     = 35

#if needed, consider adapting threshold based on proximity to previous switch,
#as multiple valid presses in succession will shift the upper and lower thresholds up slightly

    import datetime as _dt

    presscount = 0

    def _on_press():
        ts = _dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        global presscount
        presscount+=1
        print(f"{ts}  PRESS. (count: {presscount})")

    print("Listening…  (Ctrl‑C to stop)")
    listen(
        _on_press,
        upper_threshold=UPPER_THRESHOLD,
        lower_threshold=LOWER_THRESHOLD,
        blocksize=BLOCKSIZE,
        debounce_ms=DEBOUNCE_MS,
    )
