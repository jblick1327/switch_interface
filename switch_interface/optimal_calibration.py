"""Automatic calibration for clean digital switch signals."""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np


def _detect_events(
    samples: np.ndarray,
    fs: int,
    upper: float,
    lower: float,
    debounce_ms: int,
    block_size: int,
) -> int:
    """Return the number of press events detected.

    Implements a simple Schmitt trigger with dynamic baseline and
    refractory period. Processing is done in blocks of ``block_size``.
    """
    refractory = int(math.ceil((debounce_ms / 1000) * fs))
    bias = 0.0
    prev = 0.0
    cooldown = 0
    armed = True
    presses = 0

    for start in range(0, len(samples), block_size):
        block = samples[start : start + block_size]
        if armed and len(block):
            bias = 0.995 * bias + 0.005 * float(block.mean())
        dyn_upper = bias + upper
        dyn_lower = bias + lower

        arr = np.concatenate(([prev], block))
        crossings = (arr[:-1] >= dyn_upper) & (arr[1:] <= dyn_lower)

        press_idx: int | None = None
        if not armed:
            if cooldown >= len(block):
                cooldown -= len(block)
            else:
                armed = True
                offset = cooldown
                remaining = crossings[offset:]
                idxs = np.flatnonzero(remaining)
                if idxs.size:
                    press_idx = int(idxs[0] + offset)
        else:
            idxs = np.flatnonzero(crossings)
            if idxs.size:
                press_idx = int(idxs[0])

        if press_idx is not None:
            presses += 1
            armed = False
            cooldown = refractory - (len(block) - press_idx - 1)
            if cooldown <= 0:
                cooldown = 0
                armed = True
        prev = block[-1] if len(block) else prev

    return presses


_DEFAULT_BLOCK = 256


def calibrate(
    samples: np.ndarray,
    fs: int,
    target_presses: int,
    *,
    initial_gap: float = 0.30,
    search_gap: Tuple[float, float] = (0.25, 0.35),
    block_sizes: Tuple[int, ...] = (512, 256, 128, 64),
) -> dict:
    """Return optimal detection parameters for ``samples``.

    Parameters are tuned so the press count matches ``target_presses``.
    """
    # Debounce sweep using loose thresholds
    best_db = 20
    best_diff = float("inf")
    for db in range(20, 181, 20):
        cnt = _detect_events(samples, fs, -0.05, -0.80, db, _DEFAULT_BLOCK)
        diff = abs(cnt - target_presses)
        if diff < best_diff:
            best_diff = diff
            best_db = db
        if cnt == target_presses:
            best_db = db
            best_diff = diff
            break
    debounce = best_db

    # Threshold search with fixed gap
    gap = initial_gap
    low, high = -0.60, -0.05
    best_upper = high
    best_count = _detect_events(samples, fs, best_upper, best_upper - gap, debounce, _DEFAULT_BLOCK)
    best_diff = abs(best_count - target_presses)
    while high - low > 0.01:
        mid = (low + high) / 2.0
        cnt = _detect_events(samples, fs, mid, mid - gap, debounce, _DEFAULT_BLOCK)
        diff = abs(cnt - target_presses)
        if diff < best_diff:
            best_diff = diff
            best_upper = mid
            best_count = cnt
        if cnt > target_presses:
            high = mid
        elif cnt < target_presses:
            low = mid
        else:
            best_upper = mid
            best_count = cnt
            break

    final_upper = best_upper
    final_count = best_count

    # Gap fine-tuning if needed
    if final_count != target_presses:
        search_values = np.linspace(search_gap[0], search_gap[1], 5)
        best_overall_diff = best_diff
        best_gap = gap
        best_upper_val = final_upper
        best_count_val = final_count
        for g in search_values:
            low, high = -0.60, -0.05
            upper = high
            count = _detect_events(samples, fs, upper, upper - g, debounce, _DEFAULT_BLOCK)
            diff = abs(count - target_presses)
            best_local_upper = upper
            best_local_count = count
            best_local_diff = diff
            while high - low > 0.01:
                mid = (low + high) / 2.0
                c = _detect_events(samples, fs, mid, mid - g, debounce, _DEFAULT_BLOCK)
                d = abs(c - target_presses)
                if d < best_local_diff:
                    best_local_diff = d
                    best_local_upper = mid
                    best_local_count = c
                if c > target_presses:
                    high = mid
                elif c < target_presses:
                    low = mid
                else:
                    best_local_upper = mid
                    best_local_count = c
                    best_local_diff = d
                    break
            if best_local_diff < best_overall_diff:
                best_overall_diff = best_local_diff
                best_gap = g
                best_upper_val = best_local_upper
                best_count_val = best_local_count
                if best_overall_diff == 0:
                    break
        gap = best_gap
        final_upper = best_upper_val
        final_count = best_count_val

    lower = final_upper - gap

    # Block-size selection
    best_size = block_sizes[-1] if block_sizes else _DEFAULT_BLOCK
    best_diff = float("inf")
    for size in block_sizes:
        cnt = _detect_events(samples, fs, final_upper, lower, debounce, size)
        diff = abs(cnt - target_presses)
        if diff < best_diff:
            best_diff = diff
            best_size = size
        if cnt == target_presses:
            best_size = size
            break

    return {
        "upper_offset": float(final_upper),
        "lower_offset": float(lower),
        "debounce_ms": int(debounce),
        "block_size": int(best_size),
    }

