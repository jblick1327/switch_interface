import sounddevice as sd
import numpy as np

from typing import Any
CData = Any #to appease VSC

DEVICE = 1
CHANNELS = 1
SAMPLERATE = 1000


def callback(indata: np.ndarray, frames: int,
        time: CData, status: sd.CallbackFlags) -> None:
    
    if status:
        print(status)
    print(f"frames: {frames}. max amp: {np.max(np.abs(indata))}")


stream = sd.InputStream(device=DEVICE, channels=CHANNELS, samplerate=SAMPLERATE, callback=callback)

print(sd.query_devices())

#with stream:
#    input("Press Enter to stop.\n")


#switches with momentary spikes will require a higher sample rate
#switches with lots of noise will require a higher bit depth
#switches with sustained peaks or troughs can get away with a very low sample rate, 100hzish