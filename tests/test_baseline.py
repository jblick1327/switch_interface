import sys
from types import SimpleNamespace

import numpy as np

sys.modules.setdefault("sounddevice", SimpleNamespace())

from switch_interface.auto_calibration import _rolling_baseline, _choose_thresholds


def test_rolling_baseline_constant():
    fs = 1000
    t = np.arange(fs * 3)
    base = 0.25
    raw = base + 0.01 * np.sin(2 * np.pi * 5 * t / fs)
    old = np.full_like(raw, np.quantile(raw, 0.80))
    new = _rolling_baseline(raw, fs)
    assert np.allclose(new, old)


def test_rolling_baseline_ramp():
    fs = 1000
    t = np.arange(fs * 5)
    base = 0.0001 * t / t[-1]
    raw = base.copy()
    new = _rolling_baseline(raw, fs)
    assert np.max(np.abs(new - base)) <= 1 / 32768


def test_offsets_preserved():
    fs = 1000
    t = np.arange(fs * 2)
    raw = 0.5 + 0.2 * np.sin(2 * np.pi * 5 * t / fs)
    base = _rolling_baseline(raw, fs)
    up, low = _choose_thresholds(raw, base, fs)
    med = np.median(base)
    residual = raw - base
    trough_idx = (
        np.flatnonzero(
            (residual[1:-1] < residual[:-2]) & (residual[1:-1] < residual[2:])
        )
        + 1
    )
    troughs = raw[trough_idx] if trough_idx.size else np.array([raw.min()])
    expected = -0.40 * (med - np.median(troughs))
    assert abs((up - med) - expected) < 1e-6
