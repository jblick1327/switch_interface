"""Automatic parameter search for the edge detector.

This module exposes :func:`auto_calibrate` which analyses an audio clip of
switch presses and returns a :class:`~switch_interface.calibration.DetectorConfig`
with tuned ``upper_offset``, ``lower_offset`` and ``debounce_ms`` values.

The implementation follows the specification in the task description.  The
search consists of a binary search for the upper threshold, a binary search for
the debounce time and finally a linear search over a set of lower-threshold
ratios.  If multiple configurations detect exactly ``target`` presses, a
tie‑breaker based on press timing is used.
"""

from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
from typing import List, Sequence, Tuple
import warnings

import numpy as np

from .calibration import DetectorConfig


class AutoCalWarning(RuntimeWarning):
    """Raised when auto calibration fails to hit the target exactly."""


def _detect_events(
    samples: np.ndarray,
    fs: int,
    upper: float,
    lower: float,
    debounce_ms: int,
) -> List[int]:
    """Return indices of detected edges using a vectorised algorithm."""

    bias = np.zeros_like(samples)
    if len(samples) > 1:
        for i in range(1, len(samples)):
            bias[i] = 0.995 * bias[i - 1] + 0.005 * samples[i]

    dyn_upper = bias[:-1] + upper
    dyn_lower = bias[:-1] + lower
    crossings = (samples[:-1] >= dyn_upper) & (samples[1:] <= dyn_lower)
    idxs = np.flatnonzero(crossings) + 1

    refractory = int(math.ceil((debounce_ms / 1000) * fs))
    if refractory <= 1:
        return idxs.tolist()

    events: List[int] = []
    last = -refractory
    for idx in idxs:
        if idx - last >= refractory:
            events.append(int(idx))
            last = idx
    return events


def _score_events(events: Sequence[int], fs: int) -> float:
    """Return tie-breaker score for ``events``."""

    if len(events) < 2:
        return float("inf")

    gaps = np.diff(events) / fs
    slow = gaps[:3].mean() if len(gaps) >= 3 else gaps.mean()
    fast = gaps[3:].mean() if len(gaps) > 3 else slow
    return abs(slow - 0.8) + abs(fast - 0.3)


def _binary_search_threshold(
    samples: np.ndarray,
    fs: int,
    low: float,
    high: float,
    target: int,
    *,
    debounce_ms: int = 60,
    ratio: float = 1.5,
    max_iters: int = 15,
) -> Tuple[float, List[Tuple[float, int]]]:
    """Binary search the ``upper_offset`` producing ``target`` events."""

    history: List[Tuple[float, int]] = []
    best_val = high
    best_diff = float("inf")
    for _ in range(max_iters):
        mid = (low + high) / 2.0
        events = _detect_events(samples, fs, mid, mid * ratio, debounce_ms)
        count = len(events)
        history.append((mid, count))
        diff = abs(count - target)
        if diff < best_diff:
            best_diff = diff
            best_val = mid
        if count == target:
            best_val = mid
            break
        if count < target:
            high = mid
        else:
            low = mid
    return best_val, history


def _binary_search_debounce(
    samples: np.ndarray,
    fs: int,
    threshold: float,
    low: int,
    high: int,
    target: int,
    *,
    ratio: float = 1.5,
    max_iters: int = 8,
) -> Tuple[int, List[Tuple[int, int]]]:
    """Binary search the debounce duration producing ``target`` events."""

    history: List[Tuple[int, int]] = []
    best_val = high
    best_diff = float("inf")

    while low <= high and max_iters:
        max_iters -= 1
        mid = int(round(((low + high) / 2) / 20.0)) * 20
        mid = max(20, min(160, mid))
        events = _detect_events(samples, fs, threshold, threshold * ratio, mid)
        count = len(events)
        history.append((mid, count))
        diff = abs(count - target)
        if diff < best_diff:
            best_diff = diff
            best_val = mid
        if count == target:
            high = mid - 20
            continue
        if count > target:
            low = mid + 20
        else:
            high = mid - 20

    return best_val, history


def auto_calibrate(
    samples: np.ndarray,
    fs: int = 48_000,
    target: int = 10,
    max_iters: int = 15,
) -> DetectorConfig:
    """Return detector parameters that find ``target`` presses in ``samples``."""

    thr, _ = _binary_search_threshold(
        samples, fs, -0.8, -0.05, target, debounce_ms=60, ratio=1.5, max_iters=max_iters
    )

    db, _ = _binary_search_debounce(
        samples, fs, thr, 20, 160, target, ratio=1.5, max_iters=max_iters
    )

    best_ratio = 1.5
    best_events = _detect_events(samples, fs, thr, thr * best_ratio, db)
    best_diff = abs(len(best_events) - target)
    best_score = _score_events(best_events, fs) if not best_diff else float("inf")

    for ratio in (1.3, 1.4, 1.5, 1.6):
        events = _detect_events(samples, fs, thr, thr * ratio, db)
        diff = abs(len(events) - target)
        if diff > best_diff:
            continue
        score = _score_events(events, fs) if diff == 0 else float("inf")
        update = False
        if diff < best_diff:
            update = True
        elif diff == best_diff and score < best_score:
            update = True
        elif diff == best_diff and score == best_score:
            update = False
        if update:
            best_ratio = ratio
            best_events = events
            best_diff = diff
            best_score = score

    cfg = replace(
        DetectorConfig(),
        upper_offset=thr,
        lower_offset=thr * best_ratio,
        debounce_ms=db,
    )
    cfg.events = best_events  # type: ignore[attr-defined]

    if best_diff:
        warnings.warn(
            "Could not exactly match target press count", AutoCalWarning
        )

    return cfg


if __name__ == "__main__":  # pragma: no cover - manual utility
    import matplotlib.pyplot as plt

    data_path = Path(__file__).resolve().parents[1] / "tests" / "data" / "ten_presses.npy"
    data = np.load(str(data_path))
    result = auto_calibrate(data)
    print(
        f"upper={result.upper_offset:.3f} lower={result.lower_offset:.3f} debounce_ms={result.debounce_ms}"
    )

    plt.plot(data, lw=0.8)
    for idx in result.events:
        plt.axvline(idx, color="red", lw=0.5)
    plt.title("Detected switch presses")
    plt.show()

