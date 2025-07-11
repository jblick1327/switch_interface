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


# ---------------------------------------------------------------------
# helper: quick event counter using existing detection logic
# ---------------------------------------------------------------------
def _count_events(
    samples: np.ndarray,
    fs: int,
    upper: float,
    lower: float,
    debounce_ms: int,
    block: int = 64,
) -> list[int]:
    refractory = math.ceil(debounce_ms / 1000 * fs)
    state = EdgeState(armed=True, cooldown=0)
    events: list[int] = []
    for start in range(0, len(samples), block):
        block_buf = samples[start : start + block]
        state, pressed, idx = detect_edges(block_buf, state,
                                           upper, lower, refractory)
        if pressed:
            events.append(start + (idx or 0))
    return events


# ---------------------------------------------------------------------
# Phase 1 – amplitude analysis
# ---------------------------------------------------------------------
def _choose_thresholds(samples: np.ndarray) -> tuple[float, float]:
    # idle ≈ top 20 % of samples
    hi = np.percentile(samples, 80)
    # troughs ≈ minima every ≥20 ms
    inv = -samples
    distance = 20            # ms
    # convert to samples
    distance = max(1, int(distance / 1000 * len(samples) / (samples.size)))
    trough_idx, _ = np.lib.stride_tricks.sliding_window_view(
        inv, 2).argmax(axis=1).nonzero()
    troughs = samples[trough_idx]
    if troughs.size == 0:
        troughs = np.array([samples.min()])
    depth = hi - np.median(troughs)
    upper = hi - 0.40 * depth
    lower = hi - 0.70 * depth
    # ensure at least 0.25 FS gap
    if upper - lower < 0.25 * depth:
        lower = upper - 0.25 * depth
    return float(upper - hi), float(lower - hi)  # return as offsets


# ---------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------
def calibrate(samples: np.ndarray, fs: int) -> CalibResult:
    """Automatic calibration that returns data-driven thresholds."""
    # ---- Phase 1 ----
    u_off, l_off = _choose_thresholds(samples)

    # ---- Phase 2 – debounce sweep ----
    best_db = None
    best_recall = -1.0
    gt_events = _count_events(samples, fs, u_off, l_off, 10)  # rough GT
    gt_count = len(gt_events)

    for db in range(10, 61, 2):              # 10 … 60 ms in 2 ms steps
        ev = _count_events(samples, fs, u_off, l_off, db)
        recall = len(ev) / gt_count if gt_count else 0
        if recall >= 0.99:                   # no misses
            best_db = db
            break
        if recall > best_recall:
            best_recall = recall
            best_db = db

    events = _count_events(samples, fs, u_off, l_off, best_db)

    return CalibResult(
        events=events,
        upper_offset=u_off,
        lower_offset=l_off,
        debounce_ms=best_db,
        samplerate=fs,
    )