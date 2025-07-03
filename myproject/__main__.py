#TEMPORARY entrance point for testing
import argparse
import os
import threading
from queue import SimpleQueue

from .kb_layout_io import load_keyboard
from .kb_gui import VirtualKeyboard
from .pc_control import gui_to_controller, state
from .scan_engine import Scanner
from .detection import listen

# ── Parse CLI options ----------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--layout", dest="layout", default=os.getenv("LAYOUT_PATH"))
args = parser.parse_args()

vk = VirtualKeyboard(load_keyboard(args.layout), on_key=gui_to_controller, state=state)
scanner = Scanner(vk, dwell=0.6)
scanner.start()

press_queue: SimpleQueue[None] = SimpleQueue()

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
