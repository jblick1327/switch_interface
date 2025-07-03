#TEMPORARY entrance point for testing
from kb_layout_io import load_keyboard, FILE
from kb_gui        import VirtualKeyboard
from pc_control    import gui_to_controller
from scan_engine   import Scanner
from detection     import listen
import threading
from queue import SimpleQueue

# ── GUI & Scanner ───────────────────────────────────────────────────────────────
vk = VirtualKeyboard(load_keyboard(FILE), on_key=gui_to_controller)
scanner = Scanner(vk, dwell=0.6)
scanner.start()

press_queue = SimpleQueue()

# ── Detection hook ─────────────────────────────────────────────────────────────

def _on_switch():
    press_queue.put(None)

def _pump_queue():
    while not press_queue.empty():
        scanner.on_press()
    vk.root.after(10, _pump_queue)

threading.Thread(target=listen, args=(_on_switch,), daemon=True).start()
vk.root.after(10, _pump_queue)

# ── Main loop ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    vk.run()
