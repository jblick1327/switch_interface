from pynput.keyboard import Key as PynKey, Controller

kb = Controller()

def trigger_press():
    print("Press Detected")
    #placeholder

def gui_to_controller(key):
    if key.action is None:
        kb.press(key.label)
        kb.release(key.label)
    else:
        print("keep working")

#basic predictive text (letter and/or word), n-grams are probably fine for now
#linear and line-based scan