from pynput.keyboard import Key as OSKey, Controller
from .key_types import Action
from .modifier_state import ModifierState

kb = Controller()

# single source of truth for modifier state
state = ModifierState()


def _tap(k: OSKey | str):
    kb.press(k)
    kb.release(k)


def gui_to_controller(key):

    action = getattr(key, "action", None)
    mode = getattr(key, "mode", "tap")
    label = getattr(key, "label", "")

    if isinstance(action, str):
        action = Action.__members__.get(action)

    # Predictive-text keys
    if action == Action.predict_word:
        if label:
            kb.type(label + " ")
        return
    if action == Action.predict_letter:
        if label:
            kb.type(label)
        return

    os_key = None
    if isinstance(action, Action) and not action.is_virtual():
        os_key = action.to_os_key()

    # Toggle modifiers (Caps Lock, etc.)
    if mode == "toggle" and os_key:
        active = state.toggle(os_key)
        if active:
            kb.press(os_key)
        else:
            kb.release(os_key)
        return

    # Latch modifiers (one-shot Shift / Ctrl / Alt)
    if mode == "latch" and os_key:
        prev = state._latched
        state.latch(os_key)
        if prev:
            kb.release(prev)
        if state._latched:
            kb.press(state._latched)
        else:
            kb.release(os_key)
        return

    # Normal tap; apply latched modifier once if present
    def send_payload():
        if os_key is not None:
            _tap(os_key)
        else:
            kb.type(str(label))

    latched = state.consume_latch()
    if latched:
        kb.press(latched)
        send_payload()
        kb.release(latched)
    else:
        send_payload()
