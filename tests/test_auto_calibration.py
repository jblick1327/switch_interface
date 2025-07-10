import sys
from types import SimpleNamespace

sys.modules.setdefault("sounddevice", SimpleNamespace())

import numpy as np
from switch_interface.auto_calibration import auto_calibrate


def test_auto_calibrate_on_fixture():
    data = np.load("tests/data/ten_presses.npy")
    cfg = auto_calibrate(data, fs=48_000, target=10)
    assert isinstance(cfg.events, list)
    assert all(isinstance(i, int) for i in cfg.events)
    assert getattr(cfg, "autocal_method") in {"default_ok", "searched"}
    assert cfg.upper_offset > cfg.lower_offset
