from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

import numpy as np

from .detection import EdgeState, detect_edges


@dataclass
class CalibResult:
    """Placeholder structure for automatic calibration results."""

    events: List[int]
    upper_offset: float
    lower_offset: float
    debounce_ms: int
    samplerate: int


def calibrate(samples: np.ndarray, fs: int) -> CalibResult:
    """Skeleton automatic calibration routine.

    Parameters
    ----------
    samples:
        Input audio samples (mono) as a 1‑D array.
    fs:
        Sample rate of ``samples``.

    Returns
    -------
    CalibResult
        Placeholder result with hard‑coded values for now.
    """

    events = _detect_events(samples, fs)
    return CalibResult(
        events=events,
        upper_offset=-0.2,
        lower_offset=-0.5,
        debounce_ms=40,
        samplerate=fs,
    )


def _detect_events(samples: np.ndarray, fs: int) -> List[int]:
    """Detect switch events in ``samples`` using existing logic."""

    block_size = 64
    state = EdgeState(armed=True, cooldown=0)
    refractory = int(math.ceil((40 / 1000) * fs))
    events: List[int] = []
    for start in range(0, len(samples), block_size):
        block = samples[start : start + block_size]
        state, pressed, press_idx = detect_edges(
            block,
            state,
            -0.2,
            -0.5,
            refractory,
        )
        if pressed:
            events.append(start + (press_idx or 0))
    return events
