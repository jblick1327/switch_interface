"""
Minimal audio-spike button detector
  • 44.1 kHz, 256-sample blocks  (≈5.8 ms latency)
  • adaptive threshold  (peak ≥ 10 × rolling RMS)
  • 25 ms debounce  (ignores switch bounce)
  • fires callback ONCE per press (negative spike)
"""

import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd


class SwitchDetector:
    def __init__(
        self,
        on_press: Callable[[float], None],
        *,
        device: Optional[int | str] = None,
        fs: int = 44_100,
        blocksize: int = 256,
        thresh_factor: float = 10.0,
        debounce_ms: int = 25,
        rms_alpha: float = 0.90,
        channels: int = 1,
    ):
        self.on_press = on_press
        self.thresh_factor = thresh_factor
        self.debounce_s = debounce_ms / 1_000
        self.rms_alpha = rms_alpha
        self.rms_avg = 1e-6   # prevent divide-by-zero
        self.t_last = 0.0

        self.stream = sd.InputStream(
            device=device,
            samplerate=fs,
            channels=channels,
            blocksize=blocksize,
            dtype="float32",
            callback=self._callback,
        )

    def start(self) -> None:
        print("Listening …  Ctrl-C to quit")
        self.stream.start()
        try:
            while True:
                time.sleep(0.1)          # keep main thread alive
        except KeyboardInterrupt:
            pass
        finally:
            self.stream.close()

    def _callback(self, indata, frames, _time, status):
        if status:
            print(status, flush=True)

        peak = float(np.max(np.abs(indata)))
        rms_block = float(np.sqrt(np.mean(indata**2)))
        self.rms_avg = (self.rms_alpha * self.rms_avg
                        + (1.0 - self.rms_alpha) * rms_block)

        # detect negative spike = button down
        if peak > self.thresh_factor * self.rms_avg:
            # polarity of the *largest* sample in this block
            if indata[np.abs(indata).argmax()] < 0:
                now = time.time()
                if now - self.t_last >= self.debounce_s:
                    self.t_last = now
                    self.on_press(now)

if __name__ == "__main__":
    def handler(ts: float):
        print(time.strftime("%H:%M:%S", time.localtime(ts)), "PRESS")

    SwitchDetector(on_press=handler).start()
