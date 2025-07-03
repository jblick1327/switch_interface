from typing import Optional

from kb_gui import VirtualKeyboard
from key_types import Action


class Scanner:
    def __init__(
        self,
        keyboard: VirtualKeyboard,
        dwell: float = 1.0,
        reset_after_press: bool = True,
        row_column_scan: bool = False,
    ) -> None:
        self.keyboard = keyboard
        self.dwell = dwell                      # seconds each key stays lit
        self.reset_after_press = reset_after_press
        self.row_column_scan = row_column_scan  # placeholder for future modes

        self._after_id: Optional[str] = None

    def start(self) -> None:
        if self._after_id is None:
            self._tick()

    def stop(self) -> None:
        if self._after_id is not None:
            self.keyboard.root.after_cancel(self._after_id)
            self._after_id = None
    def _tick(self) -> None:
        idx = self.keyboard.highlight_index
        _, key = self.keyboard.key_widgets[idx]
        dwell_ms = int(self.dwell * 1000 * (key.dwell_mult or 1))
        self.keyboard.advance_highlight()
        self._after_id = self.keyboard.root.after(dwell_ms, self._tick)

    def on_press(self) -> None:
        """Activate the currently highlighted key."""
        _, key = self.keyboard.key_widgets[self.keyboard.highlight_index]
        action = key.action

        if action == Action.page_next:
            self.keyboard.next_page()
        elif action == Action.page_prev:
            self.keyboard.prev_page()
        elif action == Action.reset_scan_row:
            start = self.keyboard.row_start_for_index(self.keyboard.highlight_index)
            self.keyboard.highlight_index = start
            self.keyboard._update_highlight()
        else:
            self.keyboard.press_highlighted()

        if self.reset_after_press:
            self.keyboard.highlight_index = 0
            self.keyboard._update_highlight()

        if self._after_id is not None:
            self.keyboard.root.after_cancel(self._after_id)
            self._after_id = None
        self._tick()
