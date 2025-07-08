"""Command line entry point for the virtual keyboard interface."""

from __future__ import annotations

import argparse
import os
import threading
from queue import Empty, SimpleQueue

import json
from .detection import listen, check_device
from .calibration import calibrate, DetectorConfig, load_config, save_config
from .kb_gui import VirtualKeyboard
from .kb_layout_io import load_keyboard
from .pc_control import PCController
from .scan_engine import Scanner


def main(argv: list[str] | None = None) -> None:
    """Launch the scanning keyboard interface."""
    parser = argparse.ArgumentParser(
        description="Run the switch-accessible virtual keyboard",
    )
    parser.add_argument(
        "--layout",
        default=os.getenv("LAYOUT_PATH"),
        help="Path to keyboard layout JSON",
    )
    parser.add_argument(
        "--dwell",
        type=float,
        default=0.6,
        help="Time in seconds each key remains highlighted",
    )
    parser.add_argument(
        "--row-column",
        action="store_true",
        help="Use row/column scanning instead of simple linear scanning",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Show calibration sliders before launching",
    )
    args = parser.parse_args(argv)

    cfg = load_config()
    if args.calibrate:
        cfg = calibrate(cfg)
        save_config(cfg)

    try:
        check_device(
            samplerate=cfg.samplerate,
            blocksize=cfg.blocksize,
            device=cfg.device,
        )
    except RuntimeError as exc:
        raise RuntimeError("Could not open audio input device") from exc

    pc_controller = PCController()
    try:
        keyboard = load_keyboard(args.layout)
    except FileNotFoundError:
        parser.error(f"Layout file '{args.layout}' not found")
    except json.JSONDecodeError as exc:
        parser.error(f"Invalid JSON in layout file '{args.layout}': {exc.msg}")

    vk = VirtualKeyboard(
        keyboard, on_key=pc_controller.on_key, state=pc_controller.state
        )

    scanner = Scanner(vk, dwell=args.dwell, row_column_scan=args.row_column)
    scanner.start()

    press_queue: SimpleQueue[None] = SimpleQueue()

    def _on_switch() -> None:
        press_queue.put(None)

    def _pump_queue() -> None:
        while True:
            try:
                press_queue.get_nowait()
            except Empty:
                break
            scanner.on_press()
        vk.root.after(10, _pump_queue)

    threading.Thread(
        target=listen,
        args=(_on_switch, cfg),
        daemon=True,
    ).start()
    vk.root.after(10, _pump_queue)
    vk.run()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    main()
