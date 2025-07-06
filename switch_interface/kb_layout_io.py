import json
from importlib import resources
from .kb_layout import Key, KeyboardRow, KeyboardPage, Keyboard

DEFAULT_LAYOUT = 'pred_test.json'

def load_keyboard(path: str | None = None) -> Keyboard:
    """Load a :class:`Keyboard` definition from ``path`` or package data."""
    if path:
        with open(path, 'r') as file:
            blueprint = json.load(file)
    else:
        with resources.files('switch_interface.resources.layouts').joinpath(DEFAULT_LAYOUT).open('r') as file:
            blueprint = json.load(file)

    page_objects = []
    for page in blueprint['pages']:
        row_objects = []
        for row in page['rows']:
            key_objects = []
            for key in row['keys']:
                key_objects.append(
                    Key(
                        key['label'],
                        key.get('action'),
                        key.get('mode', 'tap'),
                        key.get('dwell') or key.get('dwell_mult')
                    )
                )
            row_objects.append(
                KeyboardRow(
                    key_objects,
                    stretch=row.get('stretch', True),
                )
            )
        page_objects.append(KeyboardPage(row_objects))

    return Keyboard(page_objects)
