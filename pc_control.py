from pynput.keyboard import Key as PynKey, Controller

kb = Controller()

def trigger_press():
    print("Press Detected")
    #placeholder

def gui_to_controller(key):
    pass

#connect kb_layout.Key to PynKey (with improved key_types.py)
#linear and line-based scan