from pynput.keyboard import Key as OSKey, Controller
from key_types import Action

kb = Controller()

_latched: OSKey | None = None
_toggles: set[OSKey] = set()


def _tap(k: OSKey | str):
    kb.press(k)
    kb.release(k)


def gui_to_controller(key):
    global _latched, _toggles

    action = getattr(key, "action", None)
    mode = getattr(key, "mode", "tap")
    label = getattr(key, "label", "")

    if isinstance(action, str):
        action = Action.__members__.get(action)

    # Predictive-text key: send the suggested word then a space
    if action == Action.predict_word:
        if label:
            kb.type(label + " ")
        return

    os_key = None
    if isinstance(action, Action) and not action.is_virtual():
        os_key = action.to_os_key()

    # Toggle modifiers (Caps Lock, etc.)
    if mode == "toggle" and os_key:
        if os_key in _toggles:
            kb.release(os_key)
            _toggles.remove(os_key)
        else:
            kb.press(os_key)
            _toggles.add(os_key)
        return

    # Latch modifiers (one‑shot Shift / Ctrl / Alt)
    if mode == "latch" and os_key:
        if _latched == os_key:
            kb.release(_latched)
            _latched = None
        else:
            if _latched:
                kb.release(_latched)
            kb.press(os_key)
            _latched = os_key
        return

    # Normal tap; apply latched modifier once if present
    def send_payload():
        if os_key is not None:
            _tap(os_key)
        else:
            kb.type(str(label))

    if _latched:
        kb.press(_latched)
        send_payload()
        kb.release(_latched)
        _latched = None
    else:
        send_payload()
