import importlib
import sys
import types
import contextlib
import pytest


def _reload_with_dummy_sd(monkeypatch, sd_mod):
    monkeypatch.setitem(sys.modules, "sounddevice", sd_mod)
    import switch_interface.audio.backends.wasapi_backend as wasapi
    importlib.reload(wasapi)
    return wasapi


def test_get_extra_settings_only_for_wasapi(monkeypatch):
    class DummySettings:
        def __init__(self, exclusive=False):
            self.exclusive = exclusive

    sd_mod = types.SimpleNamespace(
        WasapiSettings=DummySettings,
        query_hostapis=lambda idx: {"name": "Windows WASAPI"},
        default=types.SimpleNamespace(hostapi=0),
    )
    wasapi = _reload_with_dummy_sd(monkeypatch, sd_mod)
    assert isinstance(wasapi.get_extra_settings(), DummySettings)

    sd_mod.query_hostapis = lambda idx: {"name": "Other"}
    wasapi = _reload_with_dummy_sd(monkeypatch, sd_mod)
    assert wasapi.get_extra_settings() is None


def test_listen_retries_shared_mode(monkeypatch):
    calls = []

    @contextlib.contextmanager
    def dummy_open_input(**kwargs):
        calls.append(kwargs)
        yield

    import switch_interface.detection as detection
    import switch_interface.calibration as calibration
    importlib.reload(detection)

    monkeypatch.setattr(detection, "open_input", dummy_open_input)
    monkeypatch.setattr(detection.time, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt))

    with pytest.raises(KeyboardInterrupt):
        detection.listen(lambda: None, calibration.DetectorConfig(samplerate=1, blocksize=1))

    assert len(calls) == 1


def test_listen_raises_runtime_error(monkeypatch):
    calls = []

    @contextlib.contextmanager
    def dummy_open_input(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("fail")
        yield

    import switch_interface.detection as detection
    import switch_interface.calibration as calibration
    importlib.reload(detection)

    monkeypatch.setattr(detection, "open_input", dummy_open_input)
    monkeypatch.setattr(detection.time, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt))

    with pytest.raises(RuntimeError):
        detection.listen(lambda: None, calibration.DetectorConfig(samplerate=1, blocksize=1))

    assert len(calls) == 1
