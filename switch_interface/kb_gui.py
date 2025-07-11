import tkinter as tk
from tkinter import font
from types import SimpleNamespace
from typing import Callable

from .kb_layout import Key, Keyboard
from .key_types import Action
from .modifier_state import ModifierState
from .predictive import Predictor, default_predictor


class VirtualKeyboard:
    """Render a Keyboard as labels you cycle through and press programmatically."""

    def __init__(
        self,
        keyboard: Keyboard,
        on_key: Callable,
        state: ModifierState,
        predictor: Predictor | None = None,
    ):
        self.keyboard = keyboard
        self.on_key = on_key
        self.state = state
        self.predictor = predictor or default_predictor

        self.current_page = 0
        self.highlight_index = 0
        self.highlight_row_index: int | None = None
        self.key_widgets: list[tuple[tk.Label, Key]] = []
        self.row_start_indices: list[int] = []
        self.row_indices: list[int] = []
        self.current_word: str = ""

        self.root = tk.Tk()
        self.root.title("Virtual Keyboard")
        try:
            # Keep the window floating above others but allow resizing and
            # decoration so users can manipulate the window size.
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.93)
        except tk.TclError:
            # Attributes may fail on some platforms (e.g. dummy Tk during tests).
            pass

        self.root.resizable(True, True)

        self.page_frame = tk.Frame(self.root)
        self.page_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        try:
            from tkinter import ttk

            ttk.Sizegrip(button_frame).pack(side=tk.RIGHT, padx=(0, 5))
        except Exception:
            # Sizegrip may not be available or may fail under headless tests.
            pass

        self.font = font.nametofont("TkDefaultFont").copy()
        self.render_page()
        self.root.update_idletasks()
        self.base_font_size = self.font.cget("size")
        self.base_width = self.root.winfo_width()
        self.base_height = self.root.winfo_height()
        self.root.bind("<Configure>", self._on_resize)

    # ───────── public control API ──────────────────────────────────────────
    def advance_highlight(self):
        self.highlight_index = (self.highlight_index + 1) % len(self.key_widgets)
        self._update_highlight()

    def highlight_row(self, row_idx: int | None) -> None:
        """Highlight an entire row when row scanning."""
        self.highlight_row_index = row_idx
        self._update_highlight()

    def press_highlighted(self):
        widget, key = self.key_widgets[self.highlight_index]
        mode = getattr(key, "mode", "tap")
        action = getattr(key, "action", None)
        label = widget.cget("text")

        send_key = key
        if action == Action.predict_word:
            completion = (
                label[len(self.current_word) :]
                if label.startswith(self.current_word)
                else label
            )
            send_key = SimpleNamespace(label=completion, action=action, mode=mode)
        elif action == Action.predict_letter:
            send_key = SimpleNamespace(label=label, action=action, mode=mode)
        self.on_key(send_key)  # hand to pc_control

        # update current word buffer
        if action == Action.predict_word:
            self.current_word = ""
        elif action == Action.predict_letter and label:
            self.current_word += label.lower()
        elif action == Action.backspace:
            self.current_word = self.current_word[:-1]
        elif len(label) == 1 and label.isalpha():
            self.current_word += label.lower()
        elif action in (Action.space, Action.enter):
            self.current_word = ""
        else:
            self.current_word = ""

        self._update_predictions()

        # state.shift_armed updated automatically by OS layer

        self._refresh_letters()  # letters + tints
        self._update_highlight()  # keep yellow cursor

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
        if key.mode == "toggle" and key.action == "caps_lock" and self.state.caps_on:
            return "#b0d4ff"  # Caps tint
        if key.mode == "latch" and key.action == "shift" and self.state.shift_armed:
            return "#b0d4ff"  # Shift tint
        return "white"

    def _refresh_letters(self):
        upper = self.state.uppercase_active()
        for widget, k in self.key_widgets:
            # flip label
            if len(k.label) == 1 and k.label.isalpha():
                widget.config(text=k.label.upper() if upper else k.label.lower())
            # set base background (highlight comes later)
            widget.config(bg=self._bg_for_key(k))

    def _update_predictions(self):
        words = self.predictor.suggest_words(self.current_word, 3)
        letters = self.predictor.suggest_letters(self.current_word, 3)
        word_idx = 0
        letter_idx = 0
        for widget, k in self.key_widgets:
            act = getattr(k, "action", None)
            if act == Action.predict_word:
                label = words[word_idx] if word_idx < len(words) else ""
                widget.config(text=label)
                word_idx += 1
            elif act == Action.predict_letter:
                label = letters[letter_idx] if letter_idx < len(letters) else ""
                widget.config(text=label)
                letter_idx += 1

    def render_page(self):
        # clear out old widgets from the frame before rendering the new page
        for child in self.page_frame.winfo_children():
            child.destroy()
        self.key_widgets.clear()
        self.row_start_indices.clear()
        self.row_indices.clear()

        page = self.keyboard[self.current_page]
        max_len = max(len(r) for r in page)

        index = 0
        for r_idx, row in enumerate(page):
            row_frame = tk.Frame(self.page_frame)
            row_frame.pack(fill=tk.BOTH, expand=True)
            row_frame.grid_rowconfigure(0, weight=1)
            self.row_start_indices.append(index)

            stretch_ratio = max_len / len(row) if row.stretch and len(row) < max_len else 1

            for c_idx, key in enumerate(row):
                lbl = tk.Label(
                    row_frame,
                    text=key.label,
                    relief=tk.RAISED,
                    bd=2,
                    padx=2,
                    pady=2,
                    bg=self._bg_for_key(key),
                    font=self.font,
                )
                lbl.grid(row=0, column=c_idx, sticky="nsew")
                row_frame.grid_columnconfigure(c_idx, weight=int(stretch_ratio * 100))
                self.key_widgets.append((lbl, key))
                self.row_indices.append(r_idx)
                index += 1

        self.highlight_index = 0
        self.highlight_row_index = None
        self._update_highlight()
        self._update_predictions()

    def _update_highlight(self):
        for idx, (widget, key) in enumerate(self.key_widgets):
            if self.highlight_row_index is not None:
                bg = (
                    "orange"
                    if self.row_indices[idx] == self.highlight_row_index
                    else self._bg_for_key(key)
                )
            else:
                bg = "yellow" if idx == self.highlight_index else self._bg_for_key(key)
            widget.config(bg=bg)

    def _on_resize(self, event) -> None:
        if event.widget is not self.root:
            return
        scale_w = event.width / self.base_width if self.base_width else 1
        scale_h = event.height / self.base_height if self.base_height else 1
        scale = min(scale_w, scale_h)
        new_size = max(6, int(self.base_font_size * scale))
        self.font.configure(size=new_size)

    # ---------- main loop ----------
    def run(self):
        self.root.mainloop()
