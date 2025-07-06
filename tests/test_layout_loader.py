from switch_interface.kb_layout_io import load_keyboard

def test_default_load():
    kb = load_keyboard()
    assert len(kb) > 0
