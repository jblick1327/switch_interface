import types
from myproject.pc_control import PCController
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

def test_shift_latch_sequence():
    kb = DummyKB()
    controller = PCController(kb=kb)

    shift_key = types.SimpleNamespace(label="shift", action="shift", mode="latch")
    a_key = types.SimpleNamespace(label="a", action=None, mode="tap")
    b_key = types.SimpleNamespace(label="b", action=None, mode="tap")

    controller.on_key(shift_key)
    controller.on_key(a_key)
    controller.on_key(b_key)

    events = kb.events
    assert events[0] == ("press", OSKey.shift)
    assert events[1] == ("press", OSKey.shift)
    assert events[2] == ("type", "a")
    assert events[3] == ("release", OSKey.shift)
    assert events[4] == ("type", "b")
