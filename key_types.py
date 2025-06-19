from enum import Enum, auto

class Action(str, Enum):         
    def _generate_next_value_(name, *_):
        return name #stringington city? shall we?             
    #physical keys, directly corresponding to pynput actions
    alt        = auto()
    alt_l      = auto()
    alt_r      = auto()
    alt_gr     = auto()
    backspace  = auto()
    caps_lock  = auto()
    cmd        = auto()
    cmd_l      = auto()
    cmd_r      = auto()
    ctrl       = auto()
    ctrl_l     = auto()
    ctrl_r     = auto()
    delete     = auto()
    down       = auto()
    end        = auto()
    enter      = auto()
    esc        = auto()
    f1  = auto();  f2  = auto();  f3  = auto();  f4  = auto();  f5  = auto()
    f6  = auto();  f7  = auto();  f8  = auto();  f9  = auto();  f10 = auto()
    f11 = auto();  f12 = auto();  f13 = auto();  f14 = auto();  f15 = auto()
    f16 = auto();  f17 = auto();  f18 = auto();  f19 = auto();  f20 = auto()
    home = auto(); left = auto(); page_down = auto(); page_up = auto(); right = auto()
    shift = auto(); shift_l = auto(); shift_r = auto()
    space = auto(); tab = auto(); up = auto()
    media_play_pause   = auto(); media_volume_mute = auto()
    media_volume_down  = auto(); media_volume_up  = auto()
    media_previous     = auto(); media_next       = auto()
    insert = auto(); menu = auto(); num_lock = auto()
    pause  = auto(); print_screen = auto(); scroll_lock = auto()

    #virtual functions, user defined, etc
    page_next      = auto()  # switch to next keyboard page
    page_prev      = auto()  # switch to previous keyboard page
    reset_scan_row = auto()  # move scanner back to first key in row
    predict_word   = auto()  # predictive text (common‑word) key placeholder
    predict_letter = auto()  # predictive text (common-letter) key placeholder
    #add your own
