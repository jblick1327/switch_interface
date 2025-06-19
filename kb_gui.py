import tkinter as tk
from kb_layout import Keyboard, Key
from kb_layout_io import load_keyboard, FILE
from pc_control import gui_to_controller


class VirtualKeyboard:
    """Render a Keyboard as labels you can cycle through and ‘press’ programmatically."""

    def __init__(self, keyboard: Keyboard, on_key: callable):
        self.keyboard = keyboard
        self.on_key = on_key

        self.current_page = 0
        self.highlight_index = 0
        self.key_widgets: list[tuple[tk.Label, Key]] = []
        self.row_start_indices: list[int] = []
        self.row_indices: list[int] = []
        self.root = tk.Tk()
        self.root.title("Virtual Keyboard")

        self.page_frame = tk.Frame(self.root)
        self.page_frame.pack(padx=5, pady=5)

        self.render_page()

    # ---------- public control API ----------
    def advance_highlight(self):
        """Move highlight cursor to the next key (wrap-around)."""
        self.highlight_index = (self.highlight_index + 1) % len(self.key_widgets)
        self._update_highlight()

    def press_highlighted(self):
        """Invoke on_key callback for the currently highlighted key."""
        _, key = self.key_widgets[self.highlight_index]
        self.on_key(key)

    def next_page(self):
        if self.current_page < len(self.keyboard) - 1:
            self.current_page += 1
            self.render_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    # ---------- internal helpers ----------
    def render_page(self):
        for widget, _ in self.key_widgets:
            widget.destroy()
        self.key_widgets.clear()
        self.row_start_indices.clear()
        self.row_indices.clear()

        page = self.keyboard[self.current_page]
        max_len = max(len(r) for r in page)
        base_width = 5

        index = 0
        for r_idx, row in enumerate(page):
            row_frame = tk.Frame(self.page_frame)
            row_frame.pack(fill=tk.X)
            self.row_start_indices.append(index)
            stretch = row.stretch and len(row) < max_len
            width = int(base_width * max_len / len(row)) if stretch else base_width

            for key in row:
                lbl = tk.Label(
                    row_frame,
                    text=key.label,
                    width=width,
                    relief=tk.RAISED,
                    bd=2,
                    bg="white",
                    padx=2,
                    pady=2,
                )
                lbl.pack(side=tk.LEFT, expand=stretch)
                self.key_widgets.append((lbl, key))
                self.row_indices.append(r_idx)
                index += 1

        self.highlight_index = 0
        self._update_highlight()

    def _update_highlight(self):
        for idx, (widget, _) in enumerate(self.key_widgets):
            widget.config(bg="yellow" if idx == self.highlight_index else "white")

    def row_start_for_index(self, index: int) -> int:
        """Return the starting key index of the row containing the given key."""
        if not self.row_start_indices:
            return 0
        row_idx = self.row_indices[index]
        return self.row_start_indices[row_idx]

    # ---------- main loop ----------
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    vk = VirtualKeyboard(load_keyboard(FILE), on_key=gui_to_controller)
    vk.run()
