from __future__ import annotations

import math
import warnings
from dataclasses import replace
from typing import List, Tuple

import numpy as np

from .calibration import DetectorConfig
from .detection import EdgeState, detect_edges


class AutoCalWarning(RuntimeWarning):
    """Raised when ``auto_calibrate`` fails to hit the target exactly."""


_BLOCKSIZE = 256


def _calc_press_index(
    state: EdgeState,
    block: np.ndarray,
    upper: float,
    lower: float,
    refractory: int,
) -> int | None:
    """Return the press index within ``block`` if one occurs."""

    bias = state.bias
    if state.armed and len(block):
        bias = 0.995 * bias + 0.005 * float(block.mean())

    dyn_upper = bias + upper
    dyn_lower = bias + lower
    samples = np.concatenate(([state.prev_sample], block))
    crossings = (samples[:-1] >= dyn_upper) & (samples[1:] <= dyn_lower)

    armed = state.armed
    cooldown = state.cooldown
    press_index: int | None = None

    if not armed:
        if cooldown >= len(block):
            cooldown -= len(block)
        else:
            armed = True
            offset = cooldown
            remaining = crossings[offset:]
            idxs = np.flatnonzero(remaining)
            if idxs.size:
                press_index = int(idxs[0] + offset)
    else:
        idxs = np.flatnonzero(crossings)
        if idxs.size:
            press_index = int(idxs[0])

    if press_index is not None:
        armed = False
        cooldown = refractory - (len(block) - press_index - 1)
        if cooldown <= 0:
            cooldown = 0
            armed = True

    state = EdgeState(
        armed=armed,
        cooldown=cooldown,
        prev_sample=block[-1] if len(block) else state.prev_sample,
        bias=bias,
    )
    return press_index, state


def _offline_detect(
    samples: np.ndarray,
    fs: int,
    upper: float,
    lower: float,
    debounce_ms: int,
) -> List[int]:
    """Run ``detect_edges`` over ``samples`` and return event indices."""

    refractory = int(math.ceil((debounce_ms / 1000) * fs))
    state = EdgeState(armed=True, cooldown=0)
    events: List[int] = []

    for start in range(0, len(samples), _BLOCKSIZE):
        block = samples[start : start + _BLOCKSIZE]
        prev = state
        state, pressed = detect_edges(block, state, upper, lower, refractory)
        if pressed:
            idx, _ = _calc_press_index(prev, block, upper, lower, refractory)
            if idx is not None:
                events.append(start + idx)
    return events


def _binary_search_upper_exact(
    samples: np.ndarray,
    fs: int,
    gap: float,
    debounce_ms: int,
    target: int,
) -> Tuple[float, List[int]]:
    """Binary search ``upper_offset`` aiming for ``target`` events."""

    low, high = -0.60, -0.05
    best = high
    best_events = _offline_detect(samples, fs, best, best - gap, debounce_ms)
    best_diff = abs(len(best_events) - target)

    while high - low > 0.01:
        mid = (low + high) / 2.0
        events = _offline_detect(samples, fs, mid, mid - gap, debounce_ms)
        diff = abs(len(events) - target)
        if diff < best_diff:
            best = mid
            best_events = events
            best_diff = diff
        if len(events) > target:
            high = mid
        elif len(events) < target:
            low = mid
        else:
            best = mid
            best_events = events
            break

    return best, best_events


def _binary_search_debounce(
    samples: np.ndarray,
    fs: int,
    upper: float,
    lower: float,
    target: int,
) -> Tuple[int, List[int]]:
    """Binary search ``debounce_ms`` for ``target`` events."""

    low, high = 20, 160
    best_db = high
    best_events = _offline_detect(samples, fs, upper, lower, best_db)
    best_diff = abs(len(best_events) - target)

    while low <= high:
        mid = int(round((low + high) / 40.0)) * 20
        mid = max(20, min(160, mid))
        events = _offline_detect(samples, fs, upper, lower, mid)
        diff = abs(len(events) - target)
        if diff < best_diff or (diff == best_diff and mid < best_db):
            best_db = mid
            best_events = events
            best_diff = diff
        if diff == 0:
            break
        if len(events) > target:
            low = mid + 20
        else:
            high = mid - 20
    return best_db, best_events


def _sweep_debounce(
    samples: np.ndarray,
    fs: int,
    target: int,
    upper: float = -0.05,
    lower: float = -0.80,
) -> Tuple[int, List[int]]:
    """Return debounce giving event count closest to ``target``."""

    best_db = 20
    best_events = _offline_detect(samples, fs, upper, lower, best_db)
    best_diff = abs(len(best_events) - target)

    for db in range(40, 181, 20):
        events = _offline_detect(samples, fs, upper, lower, db)
        diff = abs(len(events) - target)
        if diff < best_diff or (diff == best_diff and db < best_db):
            best_db = db
            best_events = events
            best_diff = diff

    return best_db, best_events


def auto_calibrate(
    samples: np.ndarray,
    fs: int = 48_000,
    target: int = 10,
) -> DetectorConfig:
    """Return ``DetectorConfig`` tuned for ``samples``."""

    # Step 1 – pick debounce using loose thresholds
    debounce, events = _sweep_debounce(samples, fs, target)

    # Step 2 – binary search the upper threshold with GAP=0.30
    gap = 0.30
    upper, events = _binary_search_upper_exact(samples, fs, gap, debounce, target)

    # Step 3 – line search different gaps if needed
    if len(events) != target:
        best_diff = abs(len(events) - target)
        best_upper, best_gap, best_events = upper, gap, events
        for gap in (0.25, 0.28, 0.30, 0.32, 0.35):
            u, ev = _binary_search_upper_exact(samples, fs, gap, debounce, target)
            diff = abs(len(ev) - target)
            if diff < best_diff:
                best_diff = diff
                best_upper, best_gap, best_events = u, gap, ev
                if diff == 0:
                    break
        upper, gap, events = best_upper, best_gap, best_events

    cfg = replace(
        DetectorConfig(),
        upper_offset=upper,
        lower_offset=upper - gap,
        debounce_ms=debounce,
    )
    cfg.events = events  # type: ignore[attr-defined]
    cfg.autocal_method = "searched"  # type: ignore[attr-defined]

    if len(events) != target:
        warnings.warn(AutoCalWarning("Could not exactly match target press count"))

    return cfg
