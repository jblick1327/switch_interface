"""Simple GUI launcher for the switch interface."""

from __future__ import annotations

import tkinter as tk
from importlib import resources
from pathlib import Path

from . import __main__
from . import calibration


LAYOUT_PACKAGE = "switch_interface.resources.layouts"


def list_layouts() -> list[Path]:
    """Return available layout file paths bundled with the package."""
    files = []
    for entry in resources.files(LAYOUT_PACKAGE).iterdir():
        if entry.suffix == ".json":
            files.append(entry)
    return sorted(files)


def main() -> None:
    root = tk.Tk()
    root.title("Launch Switch Interface")

    layout_paths = list_layouts()
    layout_var = tk.StringVar(master=root)
    if layout_paths:
        layout_var.set(layout_paths[0].name)

    dwell_var = tk.DoubleVar(master=root, value=0.6)
    rowcol_var = tk.BooleanVar(master=root, value=False)

    tk.Label(root, text="Layout").pack(padx=10, pady=(10, 0))
    tk.OptionMenu(root, layout_var, *[p.name for p in layout_paths]).pack(
        fill=tk.X, padx=10
    )

    tk.Label(root, text="Dwell time (s)").pack(padx=10, pady=(10, 0))
    tk.Scale(
        root,
        variable=dwell_var,
        from_=0.1,
        to=2.0,
        resolution=0.1,
        orient=tk.HORIZONTAL,
    ).pack(fill=tk.X, padx=10)

    tk.Checkbutton(
        root, text="Row/column scanning", variable=rowcol_var
    ).pack(padx=10, pady=5)

    tk.Button(root, text="Calibrate", command=calibration.calibrate).pack(
        side=tk.LEFT, padx=10, pady=10
    )

    def _start() -> None:
        root.destroy()
        layout = resources.files(LAYOUT_PACKAGE).joinpath(layout_var.get())
        args = ["--layout", str(layout), "--dwell", str(dwell_var.get())]
        if rowcol_var.get():
            args.append("--row-column")
        __main__.main(args)

    tk.Button(root, text="Start", command=_start).pack(side=tk.RIGHT, padx=10, pady=10)

    root.mainloop()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    main()
