#TEMPORARY entrance point for testing
from kb_layout_io import load_keyboard, FILE
from kb_gui        import VirtualKeyboard
from pc_control    import gui_to_controller
from scan_engine   import Scanner
import keyboard

# ── GUI & Scanner ───────────────────────────────────────────────────────────────
vk = VirtualKeyboard(load_keyboard(FILE), on_key=gui_to_controller)
scanner = Scanner(vk, dwell=0.4)
scanner.start()

# ── Space-bar handling — suppress press *and* release, fire once per cycle ─────
def _space_down(event):
    """
    Suppress the real space character.
    We don't trigger the scanner here because key-repeat would fire many times.
    """
    event.suppress = True            # KEEP this ↓—— prevents stray spaces
    # No further action; we'll trigger on release.

def _space_up(event):
    """
    Called once when the spacebar is released.
    Fires the scanner and still keeps the space out of the OS.
    """
    event.suppress = True            # same reason as above
    scanner.on_press()

keyboard.on_press_key(  "space", _space_down,  suppress=True)
keyboard.on_release_key("space", _space_up,    suppress=True)

# ── Main loop ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    vk.run()
