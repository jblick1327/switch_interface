from __future__ import annotations

import contextlib
import importlib
import logging
import inspect
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterator, Optional, Any, Dict

import sounddevice as sd

log = logging.getLogger(__name__)

__all__ = ["open_input", "rescan_backends"]

class InputBackend:
    pass

_BACKENDS: list[InputBackend] = [] 
_BACKENDS_LOADED = False

def _discover_backends() -> None:

    global _BACKENDS_LOADED
    if _BACKENDS_LOADED:
        return

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
                    _BACKENDS.append(cls)
                except:
                    log.debug("Backend %s failed to initialize", cls.__name__)

    _BACKENDS_LOADED = True
    log.debug("Found %d functional audio back-ends: %s", len(_BACKENDS), _BACKENDS)

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
    
    _discover_backends()

    if backend is not None:
        for b in _BACKENDS:
            if b.__class__.__name__ == backend:
                chosen = b
                break
        else:
           raise RuntimeError(f"Requested backend {backend!r} not found")
    else:
        chosen = _BACKENDS[0] #maybe i should add priority values to the backend class

    with chosen.open(
    samplerate=samplerate,
    blocksize=blocksize,
    channels=channels,
    dtype=dtype,
    device=device,
    callback=callback,
    **extra_kwargs
    ) as stream:
        yield stream

def rescan_backends() -> None:
    global _BACKENDS_LOADED
    _BACKENDS_LOADED = False
    _discover_backends()
    log.debug("Re-scanning backends")