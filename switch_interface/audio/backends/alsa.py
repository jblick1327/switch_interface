from __future__ import annotations

import contextlib
import logging
from typing import Any, Callable, Iterator

import sounddevice as sd

from ..stream import InputBackend

log = logging.getLogger(__name__)


class AlsaBackend(InputBackend):
    """Backend for Linux ALSA."""

    priority = 10

    def matches_hostapi(self, hostapi_info: dict[str, Any]) -> bool:
        return "ALSA" in hostapi_info.get("name", "")

    @contextlib.contextmanager
    def open(
        self,
        *,
        samplerate: int,
        blocksize: int,
        channels: int,
        dtype: str,
        device: int | str | None,
        callback: Callable[..., None],
        **extra_kwargs: Any,
    ) -> Iterator[sd.InputStream]:
        kwargs = dict(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=channels,
            dtype=dtype,
            device=device,
            callback=callback,
        )
        kwargs.update(extra_kwargs)

        attempt_device = device
        for idx, dev in enumerate([attempt_device, "sysdefault"]):
            if idx > 0:
                kwargs["device"] = dev
            try:
                stream = sd.InputStream(**kwargs)
                stream.start()
                break
            except sd.PortAudioError as exc:
                log.debug("ALSA open failed for %s: %s", dev or "<default>", exc)
                stream = None
                continue
        if stream is None:
            raise RuntimeError("Failed to open ALSA input device")
        try:
            yield stream
        finally:
            with contextlib.suppress(Exception):
                stream.stop()
                stream.close()
