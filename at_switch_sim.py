# at_switch_sim.py  (updated – 2025‑06‑16‑c)
# -------------------------------------------------------------
# Audio‑domain simulator for assistive‑technology switches that
# are plugged into **desktop electret‑mic inputs**. Generates
# NumPy waveforms either as (1) a single full array or (2) a lazy
# block‑stream that mimics what libraries like *sounddevice* feed
# into a callback.
#
# ▶ FIX in this revision
#   ‑ Prevented **ValueError: negative dimensions** when
#     `bounce_interval_ms` is tiny (< ~0.04 ms at 48 kHz) by
#     ensuring `gap_samples ≥ 2` before subtracting 2.
# -------------------------------------------------------------
from __future__ import annotations

from typing import Iterator, Tuple
import numpy as np
from numpy.random import default_rng

__all__ = [
    "desktop_switch_press",
    "session",
    "session_stream",
]

_rng = default_rng()

# ---------------------------------------------------------------------------
#  Helper utilities
# ---------------------------------------------------------------------------

def _db_to_amp(db: float) -> float:
    """Convert dBFS to linear amplitude."""
    return 10 ** (db / 20.0)


def _noise(n: int, noise_db: float) -> np.ndarray:
    """Generate white noise at given RMS level (dBFS)."""
    amp = _db_to_amp(noise_db)
    if amp <= 0.0:
        return np.zeros(n, dtype=np.float32)
    return _rng.normal(0.0, amp, size=n).astype(np.float32)


def _trunc_normal_pos(mean: float, sd: float, floor: float = 1.0) -> float:
    """Draw from N(mean, sd) but never below *floor*."""
    x = floor - 1.0
    while x < floor:
        x = _rng.normal(mean, sd)
    return x

# ---------------------------------------------------------------------------
#  Single‑press generator
# ---------------------------------------------------------------------------

def desktop_switch_press(
    *,
    fs: int = 44_100,
    rc_ms: float = 12.0,
    bias_pop: float = 0.95,
    bounce_spikes: int = 6,
    bounce_interval_ms: float = 0.6,
    hold_ms: float = 150.0,
    noise_db: float = -70.0,
) -> np.ndarray:
    """Return **one press‑and‑hold** waveform.

    Parameters match electrical / mechanical ranges of common
    desktop‑mic + AbleNet‑class hardware.
    """
    # 1) Contact‑bounce spray ---------------------------------------------
    spike        = np.array([1.0, -1.0], dtype=np.float32)  # two‑sample edge
    # Guarantee at least 2 samples between spikes so (gap‑2) ≥ 0
    gap_samples  = max(2, int(bounce_interval_ms / 1_000 * fs))
    bounce_piece = np.concatenate([spike, np.zeros(gap_samples - 2, dtype=np.float32)])
    bounce_reg   = np.tile(bounce_piece, bounce_spikes)
    bounce_reg  += _noise(len(bounce_reg), noise_db)        # hiss while open

    # 2) Capacitor discharge pop ------------------------------------------
    discharge    = np.array([-bias_pop], dtype=np.float32)

    # 3) RC recharge -------------------------------------------------------
    rc_len       = int(rc_ms / 1_000 * fs)
    t            = np.arange(rc_len, dtype=np.float32) / fs
    rc_curve     = bias_pop * np.exp(-t / (rc_ms / 1_000)).astype(np.float32)

    # 4) Silence while held ------------------------------------------------
    silence      = np.zeros(int(hold_ms / 1_000 * fs), dtype=np.float32)

    return np.concatenate([bounce_reg, discharge, rc_curve, silence]).clip(-1, 1)

# ---------------------------------------------------------------------------
#  Session generator (single ndarray)
# ---------------------------------------------------------------------------

def session(
    *,
    fs: int = 44_100,
    n_presses: int = 20,
    mean_hold_ms: float = 180.0,
    sd_hold_ms: float = 50.0,
    mean_gap_ms: float = 380.0,
    sd_gap_ms: float = 90.0,
    rc_ms_range: Tuple[float, float] = (6.0, 20.0),
    bounce_spikes_range: Tuple[int, int] = (2, 8),
    noise_db: float = -70.0,
    noise_in_gap: bool = True,
) -> np.ndarray:
    """Return one waveform containing *n_presses* + gaps."""
    parts = []
    for _ in range(n_presses):
        rc_ms         = _rng.uniform(*rc_ms_range)
        bounce_spikes = _rng.integers(*bounce_spikes_range)  # inclusive lower
        hold_ms       = _trunc_normal_pos(mean_hold_ms, sd_hold_ms)

        parts.append(
            desktop_switch_press(fs=fs,
                                  rc_ms=rc_ms,
                                  bounce_spikes=int(bounce_spikes),
                                  hold_ms=hold_ms,
                                  noise_db=noise_db)
        )
        gap_ms   = _trunc_normal_pos(mean_gap_ms, sd_gap_ms)
        gap_len  = int(gap_ms / 1_000 * fs)
        parts.append(_noise(gap_len, noise_db) if noise_in_gap else np.zeros(gap_len, dtype=np.float32))

    return np.concatenate(parts)

# ---------------------------------------------------------------------------
#  Real‑time block stream generator
# ---------------------------------------------------------------------------

def session_stream(
    *,
    blocksize: int = 1_024,
    continuous: bool = False,
    **session_kwargs,
) -> Iterator[np.ndarray]:
    """Yield the session waveform in `blocksize` chunks (sounddevice‑style)."""
    while True:
        wav    = session(**session_kwargs)
        cursor = 0
        total  = wav.shape[0]
        while cursor < total:
            nxt = cursor + blocksize
            yield wav[cursor:nxt]
            cursor = nxt
        if not continuous:
            break
