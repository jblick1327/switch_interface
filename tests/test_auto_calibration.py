import numpy as np
from switch_interface.auto_calibration import calibrate, _detect_events


def test_calibrate_fixture():
    data = np.load("tests/data/ten_presses.npy")
    cfg = calibrate(data, fs=48_000, target_presses=10)
    assert isinstance(cfg, dict)
    assert set(cfg) == {"upper_offset", "lower_offset", "debounce_ms", "block_size"}
    assert cfg["upper_offset"] > -0.36
    assert cfg["upper_offset"] > cfg["lower_offset"]
    assert isinstance(cfg["debounce_ms"], int)
    assert isinstance(cfg["block_size"], int)
    assert cfg["debounce_ms"] <= 60
    assert 64 <= cfg["block_size"] <= 512

    assert (
        _detect_events(
            data,
            48_000,
            cfg["upper_offset"],
            cfg["lower_offset"],
            cfg["debounce_ms"],
            64,
        )
        == 10
    )
