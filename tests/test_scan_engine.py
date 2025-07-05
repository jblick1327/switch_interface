import types

from myproject.scan_engine import Scanner, ScanPhase
from myproject.key_types import Action


class DummyRoot:
    def __init__(self):
        self.scheduled = []

    def after(self, ms, func):
        self.scheduled.append(func)
        return f"id{len(self.scheduled)}"

    def after_cancel(self, after_id):
        self.scheduled.clear()


class DummyKeyboard:
    def __init__(self):
        self.root = DummyRoot()
        self.highlight_index = 0
        self.highlight_row_index = None
        self.key_widgets = [
            (None, types.SimpleNamespace(action=None, dwell_mult=None))
            for _ in range(4)
        ]
        self.row_start_indices = [0, 2]
        self.row_indices = [0, 0, 1, 1]
        self.pressed = []

    def advance_highlight(self):
        self.highlight_index = (self.highlight_index + 1) % len(self.key_widgets)

    def press_highlighted(self):
        self.pressed.append(self.highlight_index)

    def next_page(self):
        pass

    def prev_page(self):
        pass

    def row_start_for_index(self, index):
        row = self.row_indices[index]
        return self.row_start_indices[row]

    def highlight_row(self, row_idx):
        self.highlight_row_index = row_idx

    def _update_highlight(self):
        pass


def test_row_column_scanning_flow():
    kb = DummyKeyboard()
    scanner = Scanner(kb, dwell=0.1, row_column_scan=True)
    scanner.start()
    assert kb.highlight_row_index == 0
    # step to next row
    kb.root.scheduled.pop(0)()
    assert kb.highlight_row_index == 1
    # select row 1
    scanner.on_press()
    assert scanner.phase == ScanPhase.KEY
    assert kb.highlight_row_index is None
    assert kb.highlight_index == 2
    # move to next key within row
    kb.root.scheduled.pop(0)()
    assert kb.highlight_index == 3
    # activate key
    scanner.on_press()
    assert kb.pressed == [3]
    assert scanner.phase == ScanPhase.ROW
    assert kb.highlight_row_index == 0


def test_reset_after_press_starts_from_first_key():
    kb = DummyKeyboard()
    scanner = Scanner(kb, dwell=0.1)
    scanner.start()
    # advance once to highlight index 1
    kb.root.scheduled.pop(0)()
    assert kb.highlight_index == 1
    # pressing should reset the highlight back to the first key
    scanner.on_press()
    assert kb.highlight_index == 0


def test_reset_scan_row_resets_to_row_start_without_global_reset():
    kb = DummyKeyboard()
    kb.key_widgets[1] = (None, types.SimpleNamespace(action=Action.reset_scan_row, dwell_mult=None))
    scanner = Scanner(kb, dwell=0.1, reset_after_press=False)
    scanner.start()
    # advance once to highlight index 1 (the reset key)
    kb.root.scheduled.pop(0)()
    assert kb.highlight_index == 1
    # pressing reset should return to the start of the row
    scanner.on_press()
    assert kb.highlight_index == 0
    # next tick should proceed to index 1 again
    kb.root.scheduled.pop(0)()
    assert kb.highlight_index == 1
