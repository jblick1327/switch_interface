from __future__ import annotations

import contextlib
import logging
from typing import Any, Callable, Iterator

import sounddevice as sd

from ..stream import InputBackend


def get_extra_settings() -> sd.WasapiSettings | None:
    """Return exclusive-mode settings for WASAPI if available."""
    try:
        info = sd.query_hostapis(sd.default.hostapi)
        if info.get("name") == "Windows WASAPI":
            return sd.WasapiSettings(exclusive=True)
    except Exception:
        pass
    return None

log = logging.getLogger(__name__)


class WasapiBackend(InputBackend):
    """Backend for the Windows WASAPI host API."""

    priority = 20

    def matches_hostapi(self, hostapi_info: dict[str, Any]) -> bool:
        return "WASAPI" in hostapi_info.get("name", "")

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

        extra = get_extra_settings()
        if extra is not None:
            kwargs["extra_settings"] = extra
        try:
            stream = sd.InputStream(**kwargs)
            stream.start()
        except sd.PortAudioError as exc:
            if extra is None:
                raise
            log.debug("WASAPI exclusive mode failed: %s", exc)
            kwargs.pop("extra_settings", None)
            stream = sd.InputStream(**kwargs)
            stream.start()
        try:
            yield stream
        finally:
            with contextlib.suppress(Exception):
                stream.stop()
                stream.close()
