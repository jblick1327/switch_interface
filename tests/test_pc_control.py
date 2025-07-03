import types
from myproject import pc_control
from myproject.modifier_state import ModifierState
from pynput.keyboard import Key as OSKey

class DummyKB:
    def __init__(self):
        self.events = []
    def press(self, k):
        self.events.append(("press", k))
    def release(self, k):
        self.events.append(("release", k))
    def type(self, t):
        self.events.append(("type", t))

def test_shift_latch_sequence(monkeypatch):
    kb = DummyKB()
    monkeypatch.setattr(pc_control, "kb", kb)
    pc_control.state = ModifierState()

    shift_key = types.SimpleNamespace(label="shift", action="shift", mode="latch")
    a_key = types.SimpleNamespace(label="a", action=None, mode="tap")
    b_key = types.SimpleNamespace(label="b", action=None, mode="tap")

    pc_control.gui_to_controller(shift_key)
    pc_control.gui_to_controller(a_key)
    pc_control.gui_to_controller(b_key)

    events = kb.events
    assert events[0] == ("press", OSKey.shift)
    assert events[1] == ("press", OSKey.shift)
    assert events[2] == ("type", "a")
    assert events[3] == ("release", OSKey.shift)
    assert events[4] == ("type", "b")
