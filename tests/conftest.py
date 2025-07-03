import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Provide a dummy pynput backend so imports don't fail under CI
if 'pynput.keyboard' not in sys.modules:
    class _DummyKey:
        shift = 'shift'
        caps_lock = 'caps_lock'

    class _DummyController:
        def press(self, k):
            pass
        def release(self, k):
            pass
        def type(self, t):
            pass

    dummy = SimpleNamespace(Key=_DummyKey, Controller=_DummyController)
    sys.modules['pynput'] = SimpleNamespace(keyboard=dummy)
    sys.modules['pynput.keyboard'] = dummy
