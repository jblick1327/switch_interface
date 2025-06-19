from pynput.keyboard import Key as PynKey, Controller

from scanner import Scanner

kb = Controller()


def trigger_press(scanner: Scanner) -> None:
    """Callback for the switch detection loop."""
    print("Press Detected")
    scanner.on_press()


def gui_to_controller(key):
    # TODO: map Key objects to pynput
    pass

#connect kb_layout.Key to PynKey (with improved key_types.py)
