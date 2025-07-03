import threading
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

        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._reset_event = threading.Event()
        self._after_id: Optional[str] = None

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
        """Runs in a background thread, advancing the highlight at the dwell rate."""
        while self._running:
            idx, (_, cur_key) = self.keyboard.highlight_index, self.keyboard.key_widgets[self.keyboard.highlight_index]
            dwell = self.dwell * (cur_key.dwell_mult or 1)

            # Sleep, but wake early if _reset_event is set by on_press().
            if self._reset_event.wait(dwell):
                self._reset_event.clear()
                if self._after_id is not None:
                    try:
                        self.keyboard.root.after_cancel(self._after_id)
                    except Exception:
                        pass
                    self._after_id = None
                continue  # restart the dwell for the new index

            def _adv():
                self._after_id = None
                self.keyboard.advance_highlight()

            self._after_id = self.keyboard.root.after(0, _adv)

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
            self._reset_event.set()
