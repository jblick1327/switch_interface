from __future__ import annotations

import abc
import contextlib
import importlib
import inspect
import logging
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterator, Optional

import sounddevice as sd

log = logging.getLogger(__name__)

__all__ = ["open_input", "rescan_backends"]


class InputBackend(abc.ABC):
    """Abstract base class for audio input back-ends."""

    #: Higher priority back-ends are preferred when multiple match.
    priority: int = 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(priority={self.priority})"

    @abc.abstractmethod
    def matches_hostapi(self, hostapi_info: dict[str, Any]) -> bool:
        """Return ``True`` if this backend supports ``hostapi_info``."""

    @contextlib.contextmanager
    @abc.abstractmethod
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
        """Yield a started :class:`sounddevice.InputStream`."""

_BACKENDS: list[InputBackend] = []
_BACKENDS_LOADED = False

def _discover_backends() -> None:

    global _BACKENDS_LOADED
    if _BACKENDS_LOADED:
        return

    _BACKENDS.clear()

    backends_dir = Path(__file__).parent / "backends"
    for file in backends_dir.glob("*.py"):
        if file.stem == "__init__":
            continue
        module_name = f"{__package__}.backends.{file.stem}"
        try:
            mod: ModuleType = importlib.import_module(module_name)
        except ModuleNotFoundError as mnf:
            log.debug("Backend %s skipped (%s)", module_name, mnf)
            continue

        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if issubclass(cls, InputBackend) and cls is not InputBackend:
                try:
                    _BACKENDS.append(cls())
                except Exception:
                    log.debug("Backend %s failed to initialize", cls.__name__)

    _BACKENDS_LOADED = True
    _BACKENDS.sort(key=lambda b: b.priority, reverse=True)
    log.debug(
        "Found %d functional audio back-ends: %s",
        len(_BACKENDS),
        _BACKENDS,
    )


def _select_backend(device: int | str | None) -> InputBackend:
    """Return the best backend for the host API of ``device``."""

    _discover_backends()
    if not _BACKENDS:
        raise RuntimeError("No audio back-ends loaded at all")

    if device is None:
        hostapi_idx = sd.default.hostapi
    else:
        try:
            dev_info = sd.query_devices(device, "input")
            hostapi_idx = dev_info.get("hostapi", sd.default.hostapi)
        except Exception:
            hostapi_idx = sd.default.hostapi
    info = sd.query_hostapis(hostapi_idx)
    for b in _BACKENDS:
        try:
            if b.matches_hostapi(info):
                log.debug("Selected backend %s for host API %s", b, info.get("name"))
                return b
        except Exception:
            continue
    raise RuntimeError(
        f"No suitable audio back-end found for host API {info.get('name', hostapi_idx)}"
    )

@contextlib.contextmanager
def open_input(
    *,
    samplerate: int,
    blocksize: int,
    callback: Callable[..., None],
    channels: int = 1,
    dtype: str = "float32",
    device: Optional[int | str] = None,
    backend: Optional[str] = None,
    **extra_kwargs: Any,
) -> Iterator[sd.InputStream]:
    """Yield a started :class:`sounddevice.InputStream` from the best back-end."""

    _discover_backends()

    if backend is not None:
        for b in _BACKENDS:
            if b.__class__.__name__ == backend:
                chosen = b
                break
        else:
            raise RuntimeError(f"Requested backend {backend!r} not found")
    else:
        chosen = _select_backend(device)

    with chosen.open(
        samplerate=samplerate,
        blocksize=blocksize,
        channels=channels,
        dtype=dtype,
        device=device,
        callback=callback,
        **extra_kwargs,
    ) as stream:
        yield stream

def rescan_backends() -> None:
    global _BACKENDS_LOADED
    _BACKENDS_LOADED = False
    _BACKENDS.clear()
    _discover_backends()    log.debug("Re-scanning backends")
