import numpy as np, sounddevice as sd, time
from switch_interface.auto_calibration import calibrate
from switch_interface.detection import listen

FS = 48_000
TARGET = 15
print(f"▶  Press the switch exactly {TARGET} times …")
rec = sd.rec(int(17 * FS), samplerate=FS, channels=1, dtype="int16")
sd.wait()
samples = rec[:, 0].astype("float32") / 32768.0
cfg  = calibrate(samples, fs=FS, target_presses=TARGET, verbose=True)

print("\n▶  Real-time listening (Ctrl-C to stop). Press the switch at will.")
def on_press():
    print("PRESS", round(time.time(), 3))

listen(
    on_press,
    upper_offset=cfg.upper_offset,
    lower_offset=cfg.lower_offset,
    debounce_ms=cfg.debounce_ms,
    blocksize=64,
    samplerate=FS,
    device=None,         # or your device index/name
)