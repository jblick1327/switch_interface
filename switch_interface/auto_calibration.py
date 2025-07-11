"""
switch_interface/auto_calibration.py

Automatic calibration routine with detailed DEBUG logging.
Enable verbose output by passing ``verbose=True`` to ``calibrate`` or by
setting the environment variable ``SWITCH_CALIB_VERBOSE=1``.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from typing import List

import numpy as np
from scipy.signal import find_peaks

from .detection import EdgeState, detect_edges

# ------------------------------------------------------------------ #
# logging setup
# ------------------------------------------------------------------ #
logger = logging.getLogger("switch.calib")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%H:%M:%S")
    )
    logger.addHandler(_h)
logger.setLevel(logging.INFO)  # raised to DEBUG when verbose


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
def _count_events(
    samples: np.ndarray,
    fs: int,
    upper: float,
    lower: float,
    debounce_ms: int,
    block: int = 64,
    *,
    tag: str = "",
) -> list[int]:
    """Return indices of detected presses for given parameters."""
    refractory = math.ceil(debounce_ms / 1000 * fs)
    state = EdgeState(armed=True, cooldown=0)
    events: list[int] = []
    for start in range(0, len(samples), block):
        block_buf = samples[start : start + block]
        # detect_edges now returns only (state, pressed)
        state, pressed = detect_edges(block_buf, state, upper, lower, refractory)
        if pressed:
            events.append(start)          # block start is close enough
    logger.debug(
        "%s  _count_events → %d  (db=%d ms, up=%.3f, low=%.3f)",
        tag,
        len(events),
        debounce_ms,
        upper,
        lower,
    )
    return events


def _has_duplicates(events: list[int], db_ms: int, fs: int) -> bool:
    """Return True if any two successive events are closer than db_ms."""
    min_gap = db_ms * fs // 1000
    return any((b - a) < min_gap for a, b in zip(events, events[1:]))



def _choose_thresholds(
    samples: np.ndarray, fs: int, *, tag: str = ""
) -> tuple[float, float]:
    """Estimate upper/lower offsets from idle & trough statistics."""
    baseline = float(np.percentile(samples, 80))

    distance = int(0.020 * fs)  # 20 ms
    trough_idx, _ = find_peaks(-samples, distance=distance)
    troughs = samples[trough_idx] if trough_idx.size else np.array([samples.min()])
    depth = baseline - float(np.median(troughs))

    upper = baseline - 0.40 * depth
    lower = baseline - 0.70 * depth
    if upper - lower < 0.25 * depth:
        lower = upper - 0.25 * depth

    logger.debug(
        "%s  _choose_thresholds → baseline=%.4f  depth=%.4f  "
        "upper=%.4f (offset=%.4f)  lower=%.4f (offset=%.4f)",
        tag,
        baseline,
        depth,
        upper,
        upper - baseline,
        lower,
        lower - baseline,
    )
    return float(upper - baseline), float(lower - baseline)


# ------------------------------------------------------------------ #
# public API
# ------------------------------------------------------------------ #
def calibrate(
    samples: np.ndarray,
    fs: int,
    *,
    verbose: bool | None = None,
) -> CalibResult:
    """
    Derive robust thresholds and debounce time from a representative clip.

    Set verbose=True (or env var SWITCH_CALIB_VERBOSE=1) for DEBUG output.
    """
    if verbose is None:  # env-toggle wins if caller didn't specify
        verbose = os.getenv("SWITCH_CALIB_VERBOSE", "0") == "1"
    if verbose:
        logger.setLevel(logging.DEBUG)

    tag = "[CALIB]"

    # -------- Phase 1 : amplitude analysis --------
    u_off, l_off = _choose_thresholds(samples, fs, tag=tag)

    # -------- Phase 2 : debounce sweep --------
    gt_events = _count_events(samples, fs, u_off, l_off, 10, tag=f"{tag} GT")
    gt_count = len(gt_events) or 1
    logger.debug("%s  ground-truth count (10 ms debounce) = %d", tag, gt_count)

    best_db: int | None = None
    for db in range(10, 61, 2):
        ev = _count_events(samples, fs, u_off, l_off, db, tag=f"{tag} db={db}")
        recall = len(ev) / gt_count
        logger.debug("%s  debounce=%d → events=%d  recall=%.3f", tag, db, len(ev), recall)
        if recall >= 0.99:
            best_db = db
            logger.debug("%s  selected debounce=%d ms (recall≥0.99)", tag, best_db)
            break

    if best_db is None:  # fallback to best observed recall
        best_db = max(range(10, 61, 2), key=lambda d: len(_count_events(samples, fs, u_off, l_off, d)))
        logger.warning("%s  no debounce hit 0.99 recall – using %d ms", tag, best_db)

    final_events = _count_events(samples, fs, u_off, l_off, best_db, tag=f"{tag} FINAL")

    # -------- Phase 2 : robustness loop ----------------------------
    db = best_db
    u_off_final, l_off_final = u_off, l_off
    events = final_events
    max_db = 60

    while _has_duplicates(events, db, fs) and db < max_db:
        logger.debug("%s  duplicates found at %d ms → raising debounce", tag, db)
        db += 2
        events = _count_events(samples, fs, u_off, l_off, db, tag=f"{tag} db+")
    # if still duplicates at 60 ms, widen hysteresis by 5 % and retry once
    if _has_duplicates(events, db, fs):
        logger.debug("%s  widening hysteresis by 5 %%", tag)
        u_off *= 1.05
        l_off *= 1.05
        db = max(db, 20)
        events = _count_events(samples, fs, u_off, l_off, db, tag=f"{tag} wide")

    logger.info(
        "%s  FINAL  up=%.3f  low=%.3f  gap=%.3f  db=%d ms  events=%d",
        tag,
        u_off,
        l_off,
        u_off - l_off,
        db,
        len(events),
    )

    return CalibResult(
        events=events,
        upper_offset=float(u_off),
        lower_offset=float(l_off),
        debounce_ms=int(db),
        samplerate=fs,
    )
