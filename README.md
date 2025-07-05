# Switch Interface

A minimal scanning keyboard interface designed for one-switch input. It highlights keys on a virtual keyboard, listens for press signals via microphone input, and sends the selected keys to the operating system. Predictive word and letter suggestions help speed up typing.

## Running

Install the package along with its dependencies and start the interface:

```bash
pip install -e .
switch-interface --layout myproject/resources/layouts/pred_test.json
```

Use the `--layout` option to load a custom JSON layout. Example layouts are provided in `myproject/resources/layouts/`.

## Testing

The unit tests require the `wordfreq` package for predictive text features. Install it and run pytest:

```bash
pip install wordfreq
pytest
```

