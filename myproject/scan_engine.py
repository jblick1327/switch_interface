from enum import Enum, auto
from typing import Optional

from .kb_gui import VirtualKeyboard
from .key_types import Action


class ScanPhase(Enum):
    ROW = auto()
    KEY = auto()


class Scanner:
    def __init__(
        self,
        keyboard: VirtualKeyboard,
        dwell: float = 1.0,
        reset_after_press: bool = True,
        row_column_scan: bool = False,
    ) -> None:
        self.keyboard = keyboard
        self.dwell = dwell  # seconds each key stays lit
        self.reset_after_press = reset_after_press
        self.row_column_scan = row_column_scan

        self._after_id: Optional[str] = None
        self.phase = ScanPhase.ROW if row_column_scan else ScanPhase.KEY
        self.row_cursor = 0
        self.key_cursor = 0
        self.current_row = 0

    def start(self) -> None:
        if self._after_id is None:
            self._tick()

    def stop(self) -> None:
        if self._after_id is not None:
            self.keyboard.root.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self) -> None:
        if not self.row_column_scan:
            idx = self.key_cursor
            self.keyboard.highlight_index = idx
            _, key = self.keyboard.key_widgets[idx]
            dwell_ms = int(self.dwell * 1000 * (key.dwell_mult or 1))
            next_idx = (idx + 1) % len(self.keyboard.key_widgets)
            self.key_cursor = next_idx
            self.keyboard._update_highlight()
            self._after_id = self.keyboard.root.after(dwell_ms, self._tick)
            return

        if self.phase == ScanPhase.ROW:
            row_idx = self.row_cursor % len(self.keyboard.row_start_indices)
            start_idx = self.keyboard.row_start_indices[row_idx]
            self.keyboard.highlight_index = start_idx
            self.keyboard.highlight_row(row_idx)
            dwell_ms = int(self.dwell * 1000)
            self.row_cursor = (row_idx + 1) % len(self.keyboard.row_start_indices)
            self._after_id = self.keyboard.root.after(dwell_ms, self._tick)
        else:
            idx = self.key_cursor
            self.keyboard.highlight_row(None)
            self.keyboard.highlight_index = idx
            _, key = self.keyboard.key_widgets[idx]
            dwell_ms = int(self.dwell * 1000 * (key.dwell_mult or 1))
            next_idx = idx + 1
            if (
                next_idx >= len(self.keyboard.key_widgets)
                or self.keyboard.row_indices[next_idx] != self.current_row
            ):
                next_idx = self.keyboard.row_start_indices[self.current_row]
            self.key_cursor = next_idx
            self.keyboard._update_highlight()
            self._after_id = self.keyboard.root.after(dwell_ms, self._tick)

    def on_press(self) -> None:
        """Handle a switch press based on the current scan phase."""

        def _activate_highlighted() -> Action | None:
            """Activate the currently highlighted key.

            Returns the key's :class:`Action` to allow the caller to perform
            any post processing based on the action taken.
            """

            _, key = self.keyboard.key_widgets[self.keyboard.highlight_index]
            action = key.action

            if action == Action.page_next:
                self.keyboard.next_page()
            elif action == Action.page_prev:
                self.keyboard.prev_page()
            elif action == Action.reset_scan_row:
                start = self.keyboard.row_start_for_index(self.keyboard.highlight_index)
                self.keyboard.highlight_index = start
                self.key_cursor = start
                self.keyboard._update_highlight()
            else:
                self.keyboard.press_highlighted()

            return action

        if self.row_column_scan:
            if self.phase == ScanPhase.ROW:
                row_idx = (self.row_cursor - 1) % len(self.keyboard.row_start_indices)
                self.phase = ScanPhase.KEY
                self.current_row = row_idx
                self.key_cursor = self.keyboard.row_start_indices[row_idx]
                self.keyboard.highlight_row(None)
                self.keyboard.highlight_index = self.key_cursor
                self.keyboard._update_highlight()
            else:
                action = _activate_highlighted()
                if self.reset_after_press and action != Action.reset_scan_row:
                    self.row_cursor = 0
                self.phase = ScanPhase.ROW
                self.keyboard.highlight_index = self.keyboard.row_start_indices[
                    self.row_cursor
                ]
                self.keyboard.highlight_row(self.row_cursor)
        else:
            action = _activate_highlighted()
            if self.reset_after_press and action != Action.reset_scan_row:
                self.keyboard.highlight_index = 0
                self.key_cursor = 0
                self.keyboard._update_highlight()

        if self._after_id is not None:
            self.keyboard.root.after_cancel(self._after_id)
            self._after_id = None
        self._tick()
