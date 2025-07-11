from __future__ import annotations

import contextlib
import logging
from typing import Any, Callable, Iterator

import sounddevice as sd

from ..stream import InputBackend

log = logging.getLogger(__name__)


class CoreAudioBackend(InputBackend):
    """Backend for macOS Core Audio."""

    priority = 10

    def matches_hostapi(self, hostapi_info: dict[str, Any]) -> bool:
        return "Core Audio" in hostapi_info.get("name", "")

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

        stream = sd.InputStream(**kwargs)
        stream.start()
        try:
            yield stream
        finally:
            with contextlib.suppress(Exception):
                stream.stop()
                stream.close()
