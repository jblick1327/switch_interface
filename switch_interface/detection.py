from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from .audio.backends.wasapi import get_extra_settings

import numpy as np


@dataclass
class EdgeState:
    armed: bool
    cooldown: int
    prev_sample: float = 0.0
    bias: float = 0.0


def detect_edges(
    block: np.ndarray,
    state: EdgeState,
    upper_offset: float,
    lower_offset: float,
    refractory_samples: int,
) -> Tuple[EdgeState, bool]:
    """Detect a falling edge in ``block``.

    Returns the updated ``EdgeState`` and whether a press was detected.
    """

    if block.ndim != 1:
        raise ValueError(f"block must be a 1-D array (got shape {block.shape})")

    if state.armed:
        # exponential moving average over the current block
        state.bias = 0.995 * state.bias + 0.005 * float(block.mean())

    dyn_upper = state.bias + upper_offset
    dyn_lower = state.bias + lower_offset

    samples = np.concatenate(([state.prev_sample], block))
    crossings = (samples[:-1] >= dyn_upper) & (samples[1:] <= dyn_lower)

    armed = state.armed
    cooldown = state.cooldown
    press_index: int | None = None

    if not armed:
        if cooldown >= len(block):
            cooldown -= len(block)
        else:
            offset = cooldown                    # cooldown just expired
            # re-arm ONLY if the signal has risen back above dyn_upper
            if samples[offset] >= dyn_upper:
                armed = True
                remaining = crossings[offset:]
                idxs = np.flatnonzero(remaining)
                if idxs.size:
                    press_index = idxs[0] + offset
    else:
        idxs = np.flatnonzero(crossings)
        if idxs.size:
            press_index = idxs[0]

    if press_index is not None:
        armed = False
        cooldown = refractory_samples - (len(block) - press_index - 1)
        if cooldown <= 0:
            cooldown = 0
            # re-arm only after release
            if block[-1] >= dyn_upper:
                armed = True

    return (
        EdgeState(
            armed=armed,
            cooldown=cooldown,
            prev_sample=block[-1] if len(block) else state.prev_sample,
            bias=state.bias,
        ),
        press_index is not None,
    )


def check_device(
    *,
    samplerate: int = 44_100,
    blocksize: int = 256,
    device: Optional[int | str] = None,
) -> None:
    """Raise ``RuntimeError`` if the input device can't be opened."""
    import sounddevice as sd

    extra = get_extra_settings()
    kwargs = dict(
        samplerate=samplerate,
        blocksize=blocksize,
        channels=1,
        dtype="float32",
        device=device,
    )
    if extra is not None:
        kwargs["extra_settings"] = extra
    try:
        with sd.InputStream(callback=lambda *a: None, **kwargs):
            pass
    except sd.PortAudioError as exc:
        if extra is not None:
            kwargs.pop("extra_settings", None)
            try:
                with sd.InputStream(callback=lambda *a: None, **kwargs):
                    pass
            except sd.PortAudioError as exc2:
                raise RuntimeError("Failed to open audio input device") from exc2
        else:
            raise RuntimeError("Failed to open audio input device") from exc


def listen(
    on_press: Callable[[], None],
    *,
    upper_offset: float = -0.2,
    lower_offset: float = -0.5,
    samplerate: int = 44_100,
    blocksize: int = 256,
    debounce_ms: int = 40,
    device: Optional[int | str] = None,
) -> None:
    import sounddevice as sd

    if upper_offset <= lower_offset:
        raise ValueError("upper_offset must be > lower_offset (both negative values)")

    refractory_samples = int(math.ceil((debounce_ms / 1_000) * samplerate))

    state = EdgeState(armed=True, cooldown=0)

    def _callback(indata: np.ndarray, frames: int, _: int, __: int) -> None:
        nonlocal state
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]

        state, pressed = detect_edges(
            mono,
            state,
            upper_offset,
            lower_offset,
            refractory_samples,
        )
        if pressed:
            on_press()

    extra = get_extra_settings()
    stream_kwargs = dict(
        samplerate=samplerate,
        blocksize=blocksize,
        channels=1,
        dtype="float32",
        callback=_callback,
        device=device,
    )
    if extra is not None:
        stream_kwargs["extra_settings"] = extra

    def _run(kwargs):
        with sd.InputStream(**kwargs):
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                return

    try:
        _run(stream_kwargs)
    except sd.PortAudioError as exc:
        if extra is not None:
            stream_kwargs.pop("extra_settings", None)
            try:
                _run(stream_kwargs)
            except sd.PortAudioError as exc2:
                raise RuntimeError(
                    "Failed to open audio input device"
                ) from exc2
        else:
            raise RuntimeError(
                "Failed to open audio input device"
            ) from exc


if __name__ == "__main__":
    upper_offset = -0.2
    lower_offset = -0.5  # current sample must drop below this
    BLOCKSIZE = 256
    DEBOUNCE_MS = 35

    # If needed, adapt threshold based on proximity to the previous switch. Multiple
    # valid presses in succession shift the upper and lower thresholds up slightly.

    import datetime as _dt

    presscount = 0

    def _on_press() -> None:
        global presscount
        ts = _dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        presscount += 1
        print(f"{ts}  PRESS. (count: {presscount})")

    print("Listening…  (Ctrl‑C to stop)")
    listen(
        _on_press,
        upper_offset=upper_offset,
        lower_offset=lower_offset,
        blocksize=BLOCKSIZE,
        debounce_ms=DEBOUNCE_MS,
    )
