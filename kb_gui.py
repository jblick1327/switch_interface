import tkinter as tk
from kb_layout import Keyboard, Key
from kb_layout_io import load_keyboard, FILE
from pc_control import gui_to_controller

class VirtualKeyboard:
    """Render a Keyboard as labels you can cycle through and ‘press’ programmatically."""

    def __init__(self, keyboard: Keyboard, on_key: callable):
        self.keyboard = keyboard
        self.on_key   = on_key

        self.caps_on     = False
        self.shift_armed = False

        self.current_page   = 0
        self.highlight_index = 0
        self.key_widgets: list[tuple[tk.Label, Key]] = []
        self.row_start_indices: list[int] = []
        self.row_indices: list[int] = []

        self.root = tk.Tk()
        self.root.title("Virtual Keyboard")
        try:
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.93)
        except tk.TclError:
            pass

        self.page_frame = tk.Frame(self.root)
        self.page_frame.pack(padx=5, pady=5)
        self.render_page()

    # ───────── public control API ──────────────────────────────────────────
    def advance_highlight(self):
        self.highlight_index = (self.highlight_index + 1) % len(self.key_widgets)
        self._update_highlight()

    def press_highlighted(self):
        widget, key = self.key_widgets[self.highlight_index]
        mode   = getattr(key, "mode", "tap")
        action = getattr(key, "action", None)

        # update modifier state BEFORE sending to OS
        if mode == "toggle" and action == "caps_lock":
            self.caps_on = not self.caps_on
        elif mode == "latch" and action == "shift":
            self.shift_armed = not self.shift_armed

        self.on_key(key)                         # hand to pc_control

        # one-shot Shift ends right after the next tap key
        if mode == "tap" and self.shift_armed:
            self.shift_armed = False

        self._refresh_letters()                  # letters + tints
        self._update_highlight()                 # keep yellow cursor

    def next_page(self):
        if self.current_page < len(self.keyboard) - 1:
            self.current_page += 1
            self.render_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def row_start_for_index(self, index: int) -> int:
        """Return the first key index of the row containing ``index``."""
        row = self.row_indices[index]
        return self.row_start_indices[row]

    # ───────── internal helpers ───────────────────────────────────────────
    def _bg_for_key(self, key: Key) -> str:
        if key.mode == "toggle" and key.action == "caps_lock" and self.caps_on:
            return "#b0d4ff"                     # Caps tint
        if key.mode == "latch"  and key.action == "shift"    and self.shift_armed:
            return "#b0d4ff"                     # Shift tint
        return "white"

    def _refresh_letters(self):
        upper = self.caps_on or self.shift_armed
        for widget, k in self.key_widgets:
            # flip label
            if len(k.label) == 1 and k.label.isalpha():
                widget.config(text=k.label.upper() if upper else k.label.lower())
            # set base background (highlight comes later)
            widget.config(bg=self._bg_for_key(k))

    def render_page(self):
        # clear out old widgets from the frame before rendering the new page
        for child in self.page_frame.winfo_children():
            child.destroy()
        self.key_widgets.clear()
        self.row_start_indices.clear()
        self.row_indices.clear()

        page = self.keyboard[self.current_page]
        max_len   = max(len(r) for r in page)
        base_width = 5

        index = 0
        for r_idx, row in enumerate(page):
            row_frame = tk.Frame(self.page_frame)
            row_frame.pack(fill=tk.X)
            self.row_start_indices.append(index)

            stretch = row.stretch and len(row) < max_len
            width   = int(base_width * max_len / len(row)) if stretch else base_width

            for key in row:
                lbl = tk.Label(
                    row_frame, text=key.label, width=width,
                    relief=tk.RAISED, bd=2, padx=2, pady=2,
                    bg=self._bg_for_key(key)
                )
                lbl.pack(side=tk.LEFT, expand=stretch)
                self.key_widgets.append((lbl, key))
                self.row_indices.append(r_idx)
                index += 1

        self.highlight_index = 0
        self._update_highlight()

    def _update_highlight(self):
        for idx, (widget, key) in enumerate(self.key_widgets):
            bg = "yellow" if idx == self.highlight_index else self._bg_for_key(key)
            widget.config(bg=bg)

    # ---------- main loop ----------
    def run(self):
        self.root.mainloop()
