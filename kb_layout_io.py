import json
from kb_layout import Key, KeyboardRow, KeyboardPage, Keyboard

FOLDER = None
FILE = 'layouts/basic_test.json'

with open(FILE, 'r') as file:
    blueprint = json.load(file)

page_objects = []
for page in blueprint['pages']:
    row_objects = []
    for row in page['rows']:
        key_objects = []
        for key in row['keys']:
            tempaction = key['label'] #temporarily work with single letters
            key_objects.append(Key(key['label'], tempaction))
        row_objects.append(KeyboardRow(key_objects))
    page_objects.append(KeyboardPage(row_objects))

kb = Keyboard(page_objects)

