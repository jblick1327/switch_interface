from pynput.keyboard import Key as OSKey, Controller
from .interfaces import KeyReceiver
from .key_types import Action
from .modifier_state import ModifierState


class PCController(KeyReceiver):
    """Translate :class:`~switch_interface.kb_gui.Key` objects into OS key events."""

    def __init__(self, kb: Controller | None = None, state: ModifierState | None = None) -> None:
        self.kb = kb or Controller()
        # single source of truth for modifier state
        self.state = state or ModifierState()

    def _tap(self, k: OSKey | str) -> None:
        self.kb.press(k)
        self.kb.release(k)

    def on_key(self, key) -> None:
        action = getattr(key, "action", None)
        mode = getattr(key, "mode", "tap")
        label = getattr(key, "label", "")

        if isinstance(action, str):
            action = Action.__members__.get(action)

        # Predictive-text keys
        if action == Action.predict_word:
            if label:
                self.kb.type(label + " ")
            return
        if action == Action.predict_letter:
            if label:
                self.kb.type(label)
            return

        os_key = None
        if isinstance(action, Action) and not action.is_virtual():
            os_key = action.to_os_key()

        # Toggle modifiers (Caps Lock, etc.)
        if mode == "toggle" and os_key:
            active = self.state.toggle(os_key)
            if active:
                self.kb.press(os_key)
            else:
                self.kb.release(os_key)
            return

        # Latch modifiers (one-shot Shift / Ctrl / Alt)
        if mode == "latch" and os_key:
            prev = self.state._latched
            self.state.latch(os_key)
            if prev:
                self.kb.release(prev)
            if self.state._latched:
                self.kb.press(self.state._latched)
            else:
                self.kb.release(os_key)
            return

        # Normal tap; apply latched modifier once if present
        def send_payload() -> None:
            if os_key is not None:
                self._tap(os_key)
            else:
                self.kb.type(str(label))

        latched = self.state.consume_latch()
        if latched:
            self.kb.press(latched)
            send_payload()
            self.kb.release(latched)
        else:
            send_payload()
