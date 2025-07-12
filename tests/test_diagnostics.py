import logging
import math
import numpy as np
from switch_interface.auto_calibration import calibrate


def test_calibration_fails_on_noise(caplog):
    fs = 1000
    rng = np.random.default_rng(0)
    noise = 0.01 * rng.standard_normal(fs)
    with caplog.at_level(logging.WARNING, logger="switch.calib"):
        res = calibrate(noise.astype("float32"), fs, target_presses=5)
    assert not res.calib_ok
    assert any("calib_ok=False" in r.message for r in caplog.records)
    assert math.isnan(res.baseline_std) or res.baseline_std >= 0


def test_calibration_fails_bad_count(caplog):
    fs = 1000
    raw = 0.01 * np.random.default_rng(1).standard_normal(fs * 4)
    for idx in range(4):
        start = idx * fs
        raw[start : start + fs // 20] -= 0.5
    with caplog.at_level(logging.WARNING, logger="switch.calib"):
        res = calibrate(raw.astype("float32"), fs, target_presses=10)
    assert not res.calib_ok
    assert any("calib_ok=False" in r.message for r in caplog.records)
    assert math.isnan(res.baseline_std) or res.baseline_std >= 0


def test_calibration_passes():
    fs = 1000
    raw = np.zeros(fs * 5, dtype=np.float32)
    for idx in range(4):
        start = (idx + 1) * fs
        raw[start : start + fs // 20] -= 0.5
    res = calibrate(raw, fs, target_presses=4)
    assert res.calib_ok
    assert res.baseline_std > 0
    assert res.min_gap >= 0.25
