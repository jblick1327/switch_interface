#TEMPORARY entrance point for testing
from kb_layout_io import load_keyboard, FILE
from kb_gui        import VirtualKeyboard
from pc_control    import gui_to_controller
from scan_engine   import Scanner
from detection     import listen
import threading

# ── GUI & Scanner ───────────────────────────────────────────────────────────────
vk = VirtualKeyboard(load_keyboard(FILE), on_key=gui_to_controller)
scanner = Scanner(vk, dwell=0.6)
scanner.start()

# ── Detection hook ─────────────────────────────────────────────────────────────
def _on_switch():
    vk.root.after(0, scanner.on_press)

threading.Thread(target=listen, args=(_on_switch,), daemon=True).start()

# ── Main loop ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    vk.run()
