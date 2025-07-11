import numpy as np
from switch_interface.auto_calibration import calibrate, _count_events

CLIP = "calibration_long.npy"
FS   = 48_000

data = np.load(CLIP)
cfg  = calibrate(data, fs=FS, target_presses=50, verbose=True)   # prints DEBUG info
gt   = _count_events(data, FS,
                     cfg.upper_offset, cfg.lower_offset, debounce_ms=8)
from switch_interface.auto_calibration import _has_duplicates
assert len(cfg.events) == 50
assert not _has_duplicates(cfg.events, cfg.debounce_ms, FS)

precision = 1.0                                # by design, no false+
recall    = len(cfg.events) / len(gt)

print(f"\nPrecision: {precision:.3f}  Recall: {recall:.3f}")
print(cfg)
