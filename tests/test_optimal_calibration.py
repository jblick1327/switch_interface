import numpy as np
from switch_interface.optimal_calibration import calibrate


def test_calibrate_fixture():
    data = np.load("tests/data/ten_presses.npy")
    cfg = calibrate(data, fs=48_000, target_presses=10)
    assert isinstance(cfg, dict)
    assert set(cfg) == {"upper_offset", "lower_offset", "debounce_ms", "block_size"}
    assert cfg["upper_offset"] > cfg["lower_offset"]
    assert isinstance(cfg["debounce_ms"], int)
    assert isinstance(cfg["block_size"], int)
