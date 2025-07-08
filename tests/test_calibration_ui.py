import importlib
import sys
import types

import pytest


def _setup_dummy_tk(monkeypatch):
    class DummyVar:
        def __init__(self, master=None, value=None):
            self._value = value
        def get(self):
            return self._value
        def set(self, v):
            self._value = v

    class DummyCanvas:
        def __init__(self, master=None, width=0, height=0, bg=None):
            self.master = master
            master.canvas = self
        def pack(self, *args, **kwargs):
            pass
        def create_line(self, *args, **kwargs):
            pass
        def delete(self, tag):
            pass

    class DummyScale:
        def __init__(self, *args, **kwargs):
            pass
        def pack(self, *args, **kwargs):
            pass

    class DummyButton:
        def __init__(self, master=None, text=None, command=None):
            self.command = command
            master.button = self
        def pack(self, *args, **kwargs):
            pass
        def invoke(self):
            if self.command:
                self.command()

    class DummyLabel:
        def __init__(self, master=None, text=None):
            self.master = master
        def pack(self, *args, **kwargs):
            pass

    class DummyOptionMenu:
        def __init__(self, master=None, var=None, *values):
            self.master = master
        def pack(self, *args, **kwargs):
            pass

    class DummyTk:
        instance = None
        def __init__(self):
            DummyTk.instance = self
            self._bg = "default"
        def title(self, title):
            self.title = title
        def protocol(self, name, cb):
            self.cb = cb
        def after(self, ms, func):
            return 'id'
        def configure(self, **kwargs):
            if "bg" in kwargs:
                self._bg = kwargs["bg"]
        def cget(self, key):
            if key == "bg":
                return self._bg
            raise KeyError(key)
        def mainloop(self):
            if hasattr(self, 'button'):
                self.button.invoke()
        def destroy(self):
            pass

    tk_mod = types.SimpleNamespace(
        Tk=DummyTk,
        Canvas=DummyCanvas,
        Scale=DummyScale,
        Button=DummyButton,
        Label=DummyLabel,
        OptionMenu=DummyOptionMenu,
        DoubleVar=DummyVar,
        StringVar=DummyVar,
        IntVar=DummyVar,
        HORIZONTAL='horizontal',
        X='x',
        messagebox=types.SimpleNamespace(showerror=lambda *a, **k: None),
    )
    monkeypatch.setitem(sys.modules, 'tkinter', tk_mod)
    return DummyTk


def _setup_dummy_sd(monkeypatch):
    calls = []
    class DummyStream:
        def __init__(self, **kwargs):
            calls.append(kwargs)
        def start(self):
            pass
        def stop(self):
            pass
        def close(self):
            pass

    sd_mod = types.SimpleNamespace(
        InputStream=lambda **kw: DummyStream(**kw),
        PortAudioError=Exception,
        query_devices=lambda: [
            {"name": "Mic1", "max_input_channels": 1},
            {"name": "Mic2", "max_input_channels": 1},
        ],
    )
    monkeypatch.setitem(sys.modules, 'sounddevice', sd_mod)
    return calls


def test_calibrate_canvas_and_stream(monkeypatch):
    DummyTk = _setup_dummy_tk(monkeypatch)
    calls = _setup_dummy_sd(monkeypatch)
    monkeypatch.setattr('switch_interface.audio.backends.wasapi.get_extra_settings', lambda: None)
    import switch_interface.calibration as calibration
    importlib.reload(calibration)
    res = calibration.calibrate(calibration.DetectorConfig())
    assert isinstance(res, calibration.DetectorConfig)
    assert DummyTk.instance.canvas is not None
    assert len(calls) == 1
