from collections.abc import Sequence
from dataclasses import dataclass
from typing import List, Optional
from key_types import Action


@dataclass(frozen=True, slots=True)
class Key:
    label: str
    action: Optional[Action] = None
    mode: str = "tap"          # ← "tap", "latch" or "toggle"
    dwell_mult: Optional[float] = None #optional per-key multiplier for keyboard scan speed

    def __post_init__(self):
        if len(self.label) > 1 and self.action is None:
            raise ValueError(f"'action' is required when 'label' is multiple characters"
                             f"(got {self.label})")

class KeyboardRow(Sequence[Key]):
    def __init__(self, keys: List[Key], *, stretch: bool = True):
        if not keys:
            raise ValueError("KeyboardRow must contain at least one Key")
        self._keys = keys
        self.stretch = stretch

    def __len__(self) -> int:
        return len(self._keys)

    def __getitem__(self, index):
        return self._keys[index]

class KeyboardPage(Sequence[KeyboardRow]):
    def __init__(self, rows: List[KeyboardRow]):
        if not rows:
            raise ValueError("KeyboardPage must contain at least one row")
        self._rows = rows

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, index):
        return self._rows[index]

class Keyboard(Sequence[KeyboardPage]):
    def __init__(self, pages: List[KeyboardPage]):
        if not pages:
            raise ValueError("Keyboard must contain at least one page")
        self._pages = pages
        self.current_page: int = 0

    def __len__(self) -> int:
        return len(self._pages)

    def __getitem__(self, index):
        return self._pages[index]
