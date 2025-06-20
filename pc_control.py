"""Mapping of GUI key actions to OS key events using :mod:`pynput`."""

from pynput.keyboard import Key as OSKey, Controller

from key_types import Action

kb = Controller()

def _send(key: OSKey | str) -> None:
    """Press and release ``key`` using the global controller."""

    kb.press(key)
    kb.release(key)

def gui_to_controller(key) -> None:
    """Send the :mod:`pynput` events corresponding to ``key``.

    ``key`` is a :class:`kb_layout.Key` instance.  If ``key.action`` refers to
    one of the physical keys defined in :class:`Action`, the matching
    :class:`pynput.keyboard.Key` is pressed and released.  Otherwise the textual
    ``label`` of the key is typed character by character.  Virtual actions such
    as :data:`Action.page_next` are ignored here and handled elsewhere.
    """

    action = getattr(key, "action", None)

    # Convert a string action to ``Action`` if possible
    if isinstance(action, str):
        try:
            action = Action[action]
        except KeyError:
            # Unknown action string - treat as None and fall back to label
            action = None

    if isinstance(action, Action):
        if action.is_virtual():
            # These actions are handled elsewhere and should not send OS events
            return

        os_key = action.to_os_key()
        if os_key is not None:
            _send(os_key)
            return

    # Fallback to typing the label as characters
    for char in str(getattr(key, "label", "")):
        _send(char)

