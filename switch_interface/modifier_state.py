from __future__ import annotations
from dataclasses import dataclass, field
from pynput.keyboard import Key as OSKey

@dataclass
class ModifierState:
    caps_on: bool = False  # Caps Lock active
    shift_armed: bool = False  # one-shot Shift (GUI hint)
    _latched: OSKey | None = None
    _toggles: set[OSKey] = field(default_factory=set)

    def toggle(self, key: OSKey) -> bool:
        """Toggle a modifier; return True if now active."""
        if key in self._toggles:
            self._toggles.remove(key)
            if key == OSKey.caps_lock:
                self.caps_on = False
            return False
        else:
            self._toggles.add(key)
            if key == OSKey.caps_lock:
                self.caps_on = True
            return True

    def latch(self, key: OSKey) -> None:
        """Latch a modifier until the next tap."""
        if self._latched == key:
            self.shift_armed = False
            self._latched = None
        else:
            if self._latched:
                self.shift_armed = False
            self._latched = key
            if key == OSKey.shift:
                self.shift_armed = True

    def consume_latch(self) -> OSKey | None:
        """Return and clear the latched key, if any."""
        key = self._latched
        self._latched = None
        if key == OSKey.shift:
            self.shift_armed = False
        return key

    def uppercase_active(self) -> bool:
        return self.caps_on or self.shift_armed
