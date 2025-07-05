# Switch Interface

Switch Interface is a lightweight scanning keyboard for one-switch input. It highlights keys on a virtual keyboard while listening to microphone input to detect switch presses. Predictive word and letter suggestions speed up typing.

## Requirements

- Python 3.11 or newer
- Runtime dependencies (`pynput` and `wordfreq`) are installed automatically via `pip install -e .`.

## Installation

```bash
pip install -e .
```

## Usage

Launch the interface with a keyboard layout JSON file:

```bash
switch-interface --layout myproject/resources/layouts/pred_test.json
```

The CLI also accepts optional flags:

- `--dwell SECONDS` — how long each key remains highlighted (default: 0.6).
- `--row-column` — use row/column scanning instead of linear scanning.

### Layout files

Layouts live in `myproject/resources/layouts/`. Each JSON file defines `pages` containing rows of `keys`. Keys can specify a label and an action. The `pred_test.json` layout includes special `predict_word` and `predict_letter` keys that pull suggestions from the built‑in predictive text engine.

You can point `--layout` to any file in this format or set the `LAYOUT_PATH` environment variable.

## Testing

Run the unit tests after installing the project:

```bash
pytest
```
