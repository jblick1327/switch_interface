"""Automatic search for ``detect_edges`` parameters.

This module analyses an audio clip of switch presses and returns a
:class:`~switch_interface.calibration.DetectorConfig` tuned for the
``detect_edges`` algorithm.  The search procedure closely follows the
specification in ``AGENTS.md``.
"""

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


def _binary_search_upper(
    samples: np.ndarray,
    fs: int,
    gap: float,
    target: int,
    iters: int = 5,
) -> Tuple[float, List[int]]:
    """Binary search ``upper_offset`` for ``target`` events."""

    low, high = -0.60, -0.05
    best = high
    best_events: List[int] = []
    best_diff = float("inf")
    for _ in range(iters):
        mid = (low + high) / 2.0
        events = _offline_detect(samples, fs, mid, mid - gap, 80)
        diff = abs(len(events) - target)
        if diff < best_diff:
            best = mid
            best_events = events
            best_diff = diff
        if len(events) == target:
            best = mid
            best_events = events
            break
        if len(events) < target:
            high = mid
        else:
            low = mid
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


def auto_calibrate(samples: np.ndarray, fs: int = 48_000, target: int = 10) -> DetectorConfig:
    """Return ``DetectorConfig`` tuned for ``samples``."""

    default_cfg = DetectorConfig()
    events = _offline_detect(
        samples,
        fs,
        default_cfg.upper_offset,
        default_cfg.lower_offset,
        default_cfg.debounce_ms,
    )
    if len(events) == target:
        cfg = replace(
            default_cfg,
            upper_offset=default_cfg.upper_offset,
            lower_offset=default_cfg.lower_offset,
            debounce_ms=default_cfg.debounce_ms,
        )
        cfg.events = events  # type: ignore[attr-defined]
        cfg.autocal_method = "default_ok"  # type: ignore[attr-defined]
        return cfg

    best_score = float("inf")
    best_cfg: DetectorConfig | None = None
    best_events: List[int] = []

    for gap_i in range(10, 41, 5):
        gap = gap_i / 100.0
        upper, _ = _binary_search_upper(samples, fs, gap, target)
        debounce, events = _binary_search_debounce(samples, fs, upper, upper - gap, target)
        diff = abs(len(events) - target)
        gaps = np.diff(events) / fs
        std = float(np.std(gaps)) if gaps.size else 0.0
        score = diff * 1000 + std * 10 + debounce / 10
        if score < best_score or (score == best_score and debounce < (best_cfg.debounce_ms if best_cfg else float("inf"))):
            best_score = score
            best_cfg = replace(
                DetectorConfig(),
                upper_offset=upper,
                lower_offset=upper - gap,
                debounce_ms=debounce,
            )
            best_events = events

    assert best_cfg is not None  # for type checkers
    best_cfg.events = best_events  # type: ignore[attr-defined]
    best_cfg.autocal_method = "searched"  # type: ignore[attr-defined]

    if len(best_events) != target:
        warnings.warn(AutoCalWarning("Could not exactly match target press count"))

    return best_cfg
