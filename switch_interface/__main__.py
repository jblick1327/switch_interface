"""Command line entry point for the virtual keyboard interface."""

from __future__ import annotations

import argparse
import os
import threading
from queue import Empty, SimpleQueue

from .detection import listen
from .calibration import calibrate, DetectorConfig
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

    pc_controller = PCController()
    vk = VirtualKeyboard(
        load_keyboard(args.layout), on_key=pc_controller.on_key, state=pc_controller.state
    )
    scanner = Scanner(vk, dwell=args.dwell, row_column_scan=args.row_column)
    scanner.start()

    cfg = calibrate() if args.calibrate else DetectorConfig()

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
        args=(_on_switch,),
        daemon=True,
        kwargs=dict(
            upper_offset=cfg.upper_offset,
            lower_offset=cfg.lower_offset,
            samplerate=cfg.samplerate,
            blocksize=cfg.blocksize,
            debounce_ms=cfg.debounce_ms,
        ),
    ).start()
    vk.root.after(10, _pump_queue)
    vk.run()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    main()
