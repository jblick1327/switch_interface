"""Simple dwell-based scanner interface for the virtual keyboard."""

from __future__ import annotations

import threading
import time
from typing import Optional

from kb_gui import VirtualKeyboard
from key_types import Action


class Scanner:
    """Advance keyboard highlight on a timer and trigger presses."""

    def __init__(self, keyboard: VirtualKeyboard, dwell: float = 1.0) -> None:
        self.keyboard = keyboard
        self.dwell = dwell
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------
    def start(self) -> None:
        """Start automatic scanning in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop scanning."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=0)
            self._thread = None

    # ------------------------------------------------------------
    def _loop(self) -> None:
        while self._running:
            time.sleep(self.dwell)
            self.keyboard.root.after(0, self.keyboard.advance_highlight)

    # ------------------------------------------------------------
    def on_press(self) -> None:
        """Handle a switch press."""
        lbl, key = self.keyboard.key_widgets[self.keyboard.highlight_index]
        action = key.action
        if action == Action.page_next:
            self.keyboard.next_page()
        elif action == Action.page_prev:
            self.keyboard.prev_page()
        elif action == Action.reset_scan:
            self.keyboard.highlight_index = 0
            self.keyboard._update_highlight()
        else:
            self.keyboard.press_highlighted()
