#omg i hate tkinter

import tkinter as tk
from kb_layout import Keyboard, Key
from kb_layout_io import load_keyboard, FILE

class VirtualKeyboard:
    def __init__(self, keyboard: Keyboard):
        self.keyboard = keyboard
        self.current_page = 0
        self.highlight_index = 0
        self.key_widgets = []   # flat list of (widget, Key)

        self.root = tk.Tk()
        self.root.title("Virtual Keyboard")

        self.entry = tk.Entry(self.root)
        self.entry.pack(fill=tk.X, padx=5, pady=5)

        self.page_frame = tk.Frame(self.root)
        self.page_frame.pack(padx=5, pady=5)

        # Bind your external triggers (e.g. hardware buttons) here:
        #   self.root.bind("<Right>", lambda e: self.advance_highlight())
        #   self.root.bind("<Return>", lambda e: self.press_highlighted())

        self.render_page()

    def render_page(self):
        # clear out old widgets
        for w,_ in self.key_widgets:
            w.destroy()
        self.key_widgets.clear()

        page = self.keyboard[self.current_page]
        max_len = max(len(r) for r in page)
        base_width = 5

        for row in page:
            row_frame = tk.Frame(self.page_frame)
            row_frame.pack(fill=tk.X)
            stretch = row.stretch and len(row) < max_len
            width = int(base_width * max_len / len(row)) if stretch else base_width

            for key in row:
                lbl = tk.Label(
                    row_frame,
                    text=key.label,
                    width=width,
                    relief=tk.RAISED,
                    bd=2,
                    padx=2, pady=2,
                    bg="white"
                )
                lbl.pack(side=tk.LEFT, expand=stretch)
                self.key_widgets.append((lbl, key))

        # reset highlight to first key on this page
        self.highlight_index = 0
        self._update_highlight()

    def _update_highlight(self):
        # go through all keys, reset bg, then highlight the one at highlight_index
        for i, (w, _) in enumerate(self.key_widgets):
            w.config(bg="yellow" if i == self.highlight_index else "white")

    def advance_highlight(self):
        # move to next key (wrap around)
        self.highlight_index = (self.highlight_index + 1) % len(self.key_widgets)
        self._update_highlight()

    def press_highlighted(self):
        # simulate a press on the highlighted key
        _, key = self.key_widgets[self.highlight_index]
        self.on_press(key)

    def on_press(self, key: Key):
        if isinstance(key.action, str):
            self.entry.insert(tk.END, key.action)
        else:
            self.entry.insert(tk.END, key.label)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    vk = VirtualKeyboard(load_keyboard(FILE))
    vk.run()
