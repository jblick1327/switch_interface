"""
switch_interface/auto_calibration.py
------------------------------------

Fast, data-driven calibration for clean digital-switch signals.

• Pass ``verbose=True`` or set ``SWITCH_CALIB_VERBOSE=1`` for DEBUG logs.
• Public API:
      calibrate(samples, fs, *, target_presses=None, verbose=None) -> CalibResult
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import List

import numpy as np
from scipy.signal import find_peaks

from .detection import EdgeState, detect_edges

# ------------------------------------------------------------------ #
# logging
# ------------------------------------------------------------------ #
logger = logging.getLogger("switch.calib")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%H:%M:%S"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)              # DEBUG when verbose


# ------------------------------------------------------------------ #
# result container
# ------------------------------------------------------------------ #
@dataclass
class CalibResult:
    events: List[int]
    upper_offset: float
    lower_offset: float
    debounce_ms: int
    samplerate: int


# ------------------------------------------------------------------ #
# helpers
# ------------------------------------------------------------------ #
def _choose_thresholds(samples: np.ndarray, fs: int, *, tag: str = "") -> tuple[float, float]:
    baseline = float(np.percentile(samples, 80))
    trough_idx, _ = find_peaks(-samples, distance=int(0.020 * fs))
    troughs = samples[trough_idx] if trough_idx.size else np.array([samples.min()])
    depth = baseline - float(np.median(troughs))

    upper = baseline - 0.40 * depth
    lower = baseline - 0.70 * depth
    if (upper - lower) < 0.25 * depth:          # enforce a minimum gap
        lower = upper - 0.25 * depth

    logger.debug(
        "%s  _choose_thresholds → baseline=%.4f  depth=%.4f  "
        "upper=%.4f (off=%.4f)  lower=%.4f (off=%.4f)",
        tag,
        baseline,
        depth,
        upper,
        upper - baseline,
        lower,
        lower - baseline,
    )
    return float(upper - baseline), float(lower - baseline)


def _has_duplicates(events: list[int], db_ms: int, fs: int) -> bool:
    min_gap = db_ms * fs // 1000
    return any((b - a) < min_gap for a, b in zip(events, events[1:]))


def _count_events(
    samples: np.ndarray,
    fs: int,
    upper: float,
    lower: float,
    debounce_ms: int,
    block: int = 64,
) -> list[int]:
    """Return *indices* of detected presses – memoised for speed."""
    return _memoised_count(
        samples.tobytes(),        # hashable key
        samples.dtype.str,        # original dtype!
        samples.size,
        fs,
        upper,
        lower,
        debounce_ms,
        block,
    )


@lru_cache(maxsize=256)
def _memoised_count(
    buf: bytes,
    dtype_str: str,
    n: int,
    fs: int,
    upper: float,
    lower: float,
    debounce_ms: int,
    block: int,
) -> tuple[int]:
    """Immutable tuple result so lru_cache can store it safely."""
    samples = np.frombuffer(buf, dtype=np.dtype(dtype_str), count=n)

    refractory = math.ceil(debounce_ms / 1000 * fs)
    state = EdgeState(armed=True, cooldown=0)
    events: list[int] = []

    for start in range(0, len(samples), block):
        blk = samples[start : start + block]
        state, pressed = detect_edges(blk, state, upper, lower, refractory)
        if pressed:
            events.append(start)

    return tuple(events)


# ------------------------------------------------------------------ #
# public API
# ------------------------------------------------------------------ #
def calibrate(
    samples: np.ndarray,
    fs: int,
    *,
    target_presses: int | None = None,
    verbose: bool | None = None,
) -> CalibResult:

    if verbose is None:
        verbose = os.getenv("SWITCH_CALIB_VERBOSE", "0") == "1"
    if verbose:
        logger.setLevel(logging.DEBUG)

    tag = "[CALIB]"

    # ---- Phase 0: first-guess thresholds --------------------------- #
    u_off, l_off = _choose_thresholds(samples, fs, tag=tag)

    # ---- Phase 1: choose debounce --------------------------------- #
    db_list = range(10, 61, 2)
    best_db = 10
    best_events = _count_events(samples, fs, u_off, l_off, best_db)
    score = lambda ev: abs(len(ev) - (target_presses or len(ev)))

    if target_presses is not None:
        best_err = score(best_events)
        for d in db_list[1:]:
            ev = _count_events(samples, fs, u_off, l_off, d)
            err = score(ev)
            if err == 0:
                best_db, best_events = d, ev
                logger.debug("%s  debounce=%d → EXACT match %d presses", tag, d, target_presses)
                break
            if err < best_err:
                best_db, best_events, best_err = d, ev, err
        if best_err:
            logger.warning("%s  no exact debounce; using %d ms (count=%d)", tag, best_db, len(best_events))
    else:
        ref = _count_events(samples, fs, u_off, l_off, 10)
        ref_n = max(1, len(ref))
        for d in db_list[1:]:
            ev = _count_events(samples, fs, u_off, l_off, d)
            if len(ev) / ref_n >= 0.98:
                best_db, best_events = d, ev
                break

    # ---- Phase 2: one hysteresis tweak if still off --------------- #
    if target_presses is not None and len(best_events) != target_presses:
        direction = 1 if len(best_events) < target_presses else -1
        scale = 1.0
        for _ in range(4):
            scale *= 1.15 ** direction
            ev = _count_events(samples, fs, u_off * scale, l_off * scale, best_db)
            if len(ev) == target_presses:
                u_off, l_off, best_events = u_off * scale, l_off * scale, ev
                break
            if score(ev) < score(best_events):
                u_off, l_off, best_events = u_off * scale, l_off * scale, ev

    # ---- Phase 3: ensure no double-fires -------------------------- #
    while _has_duplicates(list(best_events), best_db, fs) and best_db < 60:
        best_db += 2
        best_events = _count_events(samples, fs, u_off, l_off, best_db)

    logger.info(
        "%s  FINAL up=%.3f  low=%.3f  gap=%.3f  db=%d ms  events=%d",
        tag,
        u_off,
        l_off,
        u_off - l_off,
        best_db,
        len(best_events),
    )

    return CalibResult(
        events=list(best_events),
        upper_offset=float(u_off),
        lower_offset=float(l_off),
        debounce_ms=int(best_db),
        samplerate=fs,
    )
