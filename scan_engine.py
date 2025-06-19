import threading
import time
from typing import Optional

from kb_gui import VirtualKeyboard
from key_types import Action


class Scanner:
    def __init__(self, keyboard: VirtualKeyboard, dwell: float = 1.0,
                 reset_after_press: bool = True, row_column_scan: bool = False) -> None:
        self.keyboard = keyboard
        self.dwell = dwell #in seconds
        self.reset_after_press = reset_after_press
        self.row_column_scan = row_column_scan
        self._running = False
        self._thread: Optional[threading.Thread] = None 

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _loop(self) -> None:
        while self._running:
            time.sleep(self.dwell)
            self.keyboard.root.after(0, self.keyboard.advance_highlight) #gpt helped me i hate tk

    def on_press(self) -> None:
        lbl, key = self.keyboard.key_widgets[self.keyboard.highlight_index]
        action = key.action
        if action == Action.page_next:
            self.keyboard.next_page()
        elif action == Action.page_prev:
            self.keyboard.prev_page()
        elif action == Action.reset_scan_row:
            start_idx = self.keyboard.row_start_for_index(self.keyboard.highlight_index)
            self.keyboard.highlight_index = start_idx
            self.keyboard._update_highlight()
        else:
            self.keyboard.press_highlighted()
        
        if self.reset_after_press:
            self.keyboard.highlight_index = 0
            self.keyboard._update_highlight()