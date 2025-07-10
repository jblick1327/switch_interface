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
        if not len(block):
            continue
        dyn_lower = bias + lower
        valid = block[block > dyn_lower]
        if valid.size:
            bias = 0.99 * bias + 0.01 * float(valid.mean())
        dyn_upper = bias + upper
        dyn_lower = bias + lower

        arr = np.concatenate(([prev], block))
        down = (arr[1:] <= dyn_lower) & (arr[:-1] > dyn_lower)

        press_idx: int | None = None
        if armed:
            idxs = np.flatnonzero(down)
            if idxs.size:
                press_idx = int(idxs[0])
        else:
            if cooldown > len(block):
                cooldown -= len(block)
                if cooldown == 0 and block[-1] >= dyn_upper:
                    armed = True
            else:
                offset = cooldown
                cooldown = 0
                up = arr[offset:] >= dyn_upper
                if np.any(up):
                    rearm_at = int(np.flatnonzero(up)[0] + offset)
                    armed = True
                    idxs = np.flatnonzero(down[rearm_at:])
                    if idxs.size:
                        press_idx = int(idxs[0] + rearm_at)

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
    """Return optimal detection parameters for ``samples``."""

    DEFAULTS = dict(
        upper_offset=-0.20,
        lower_offset=-0.50,
        debounce_ms=35,
        block_size=128,
    )

    small_block = min(block_sizes) if block_sizes else 64
    count = _detect_events(
        samples,
        fs,
        DEFAULTS["upper_offset"],
        DEFAULTS["lower_offset"],
        DEFAULTS["debounce_ms"],
        small_block,
    )
    if count == target_presses:
        return DEFAULTS.copy()

    upper_grid = np.linspace(-0.40, -0.05, 10)
    gap_grid = np.linspace(0.25, 0.35, 5)
    debounce_vals = range(20, 181, 20)

    candidates: list[tuple[float, int, float, float, int]] = []
    for u in upper_grid:
        for g in gap_grid:
            l = u - g
            for db in debounce_vals:
                c = _detect_events(samples, fs, u, l, db, small_block)
                candidates.append((abs(c - target_presses), c, u, l, db))

    candidates.sort(key=lambda t: t[0])
    top8 = candidates[:8]

    best_diff = float("inf")
    best_u = DEFAULTS["upper_offset"]
    best_gap = DEFAULTS["upper_offset"] - DEFAULTS["lower_offset"]
    best_db = DEFAULTS["debounce_ms"]

    for _, cnt, u0, l0, db0 in top8:
        u_low, u_high = u0 - 0.1, u0 + 0.1
        g_low, g_high = 0.22, 0.38
        db_low, db_high = max(20, db0 - 20), db0 + 20
        local_best_diff = float("inf")
        local_best_u = u0
        local_best_g = u0 - l0
        local_best_db = db0

        while u_high - u_low > 0.005 or g_high - g_low > 0.005 or db_high - db_low > 5:
            u_mid = (u_high + u_low) / 2
            g_mid = (g_high + g_low) / 2
            db_mid = (db_high + db_low) / 2
            count = _detect_events(
                samples,
                fs,
                u_mid,
                u_mid - g_mid,
                int(round(db_mid)),
                small_block,
            )
            diff = abs(count - target_presses)
            if diff < local_best_diff or (
                diff == local_best_diff and int(round(db_mid)) < local_best_db
            ):
                local_best_diff = diff
                local_best_u = u_mid
                local_best_g = g_mid
                local_best_db = int(round(db_mid))

            if count > target_presses:
                u_low = u_mid
                g_low = g_mid
                db_low = db_mid
            else:
                u_high = u_mid
                g_high = g_mid
                db_high = db_mid

        if local_best_diff < best_diff or (
            local_best_diff == best_diff and local_best_db < best_db
        ):
            best_diff = local_best_diff
            best_u = local_best_u
            best_gap = local_best_g
            best_db = local_best_db

    best_l = best_u - best_gap

    best_block = small_block
    for size in sorted(block_sizes):
        cnt = _detect_events(samples, fs, best_u, best_l, best_db, size)
        if cnt == target_presses:
            best_block = size
            break

    cnt = _detect_events(samples, fs, best_u, best_l, best_db, small_block)
    if cnt != target_presses:
        raise RuntimeError(f"search failed: expected {target_presses}, got {cnt}")

    return {
        "upper_offset": float(best_u),
        "lower_offset": float(best_l),
        "debounce_ms": int(best_db),
        "block_size": int(best_block),
    }
