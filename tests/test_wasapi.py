import importlib
import sys
import types
import pytest


def _reload_with_dummy_sd(monkeypatch, sd_mod):
    monkeypatch.setitem(sys.modules, "sounddevice", sd_mod)
    import switch_interface.audio.backends.wasapi as wasapi
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
    fail = {"flag": True}

    class DummySettings:
        def __init__(self, exclusive=True):
            self.exclusive = exclusive

    class PortAudioError(Exception):
        pass

    def InputStream(**kwargs):
        calls.append(kwargs)
        if fail["flag"] and "extra_settings" in kwargs:
            fail["flag"] = False
            raise PortAudioError("fail")

        class _Ctx:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Ctx()

    sd_mod = types.SimpleNamespace(
        WasapiSettings=DummySettings,
        PortAudioError=PortAudioError,
        InputStream=InputStream,
        query_hostapis=lambda idx: {"name": "Windows WASAPI"},
        default=types.SimpleNamespace(hostapi=0),
    )

    wasapi = _reload_with_dummy_sd(monkeypatch, sd_mod)
    import switch_interface.detection as detection
    importlib.reload(detection)

    monkeypatch.setattr(detection.time, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt))

    detection.listen(lambda: None, samplerate=1, blocksize=1)

    assert len(calls) == 2
    assert "extra_settings" in calls[0]
    assert "extra_settings" not in calls[1]


def test_listen_raises_runtime_error(monkeypatch):
    calls = []

    class DummySettings:
        def __init__(self, exclusive=True):
            self.exclusive = exclusive

    class PortAudioError(Exception):
        pass

    def InputStream(**kwargs):
        calls.append(kwargs)
        raise PortAudioError("fail")

    sd_mod = types.SimpleNamespace(
        WasapiSettings=DummySettings,
        PortAudioError=PortAudioError,
        InputStream=InputStream,
        query_hostapis=lambda idx: {"name": "Windows WASAPI"},
        default=types.SimpleNamespace(hostapi=0),
    )

    wasapi = _reload_with_dummy_sd(monkeypatch, sd_mod)
    import switch_interface.detection as detection
    importlib.reload(detection)

    monkeypatch.setattr(detection.time, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt))

    with pytest.raises(RuntimeError):
        detection.listen(lambda: None, samplerate=1, blocksize=1)

    assert len(calls) == 2
