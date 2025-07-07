from dataclasses import dataclass, asdict
import json
import os
import tkinter as tk

@dataclass
class DetectorConfig:
    upper_offset: float = -0.2
    lower_offset: float = -0.5
    samplerate: int = 44_100
    blocksize: int = 256
    debounce_ms: int = 40


CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".switch_interface")
CONFIG_FILE = os.path.join(CONFIG_DIR, "detector.json")


def load_config(path: str = CONFIG_FILE) -> "DetectorConfig":
    """Return saved detector settings or defaults if unavailable."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return DetectorConfig(**data)
    except Exception:
        return DetectorConfig()


def save_config(config: "DetectorConfig", path: str = CONFIG_FILE) -> None:
    """Persist ``config`` to ``path`` in JSON format."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f)


def calibrate(config: DetectorConfig | None = None) -> DetectorConfig:
    """Launch a simple UI to adjust detector settings."""
    config = config or DetectorConfig()
    root = tk.Tk()
    root.title("Calibrate Detector")

    u_var = tk.DoubleVar(master=root, value=config.upper_offset)
    l_var = tk.DoubleVar(master=root, value=config.lower_offset)
    sr_var = tk.IntVar(master=root, value=config.samplerate)
    bs_var = tk.IntVar(master=root, value=config.blocksize)
    db_var = tk.IntVar(master=root, value=config.debounce_ms)

    tk.Scale(
        root,
        variable=u_var,
        from_=-1.0,
        to=1.0,
        resolution=0.01,
        label="Upper offset",
        orient=tk.HORIZONTAL,
    ).pack(fill=tk.X, padx=10, pady=5)

    tk.Scale(
        root,
        variable=l_var,
        from_=-1.0,
        to=0.0,
        resolution=0.01,
        label="Lower offset",
        orient=tk.HORIZONTAL,
    ).pack(fill=tk.X, padx=10, pady=5)

    tk.Scale(
        root,
        variable=sr_var,
        from_=100,
        to=96_000,
        resolution=1_000,
        label="Sample rate",
        orient=tk.HORIZONTAL,
    ).pack(fill=tk.X, padx=10, pady=5)

    tk.Scale(
        root,
        variable=bs_var,
        from_=64,
        to=1024,
        resolution=64,
        label="Block size",
        orient=tk.HORIZONTAL,
    ).pack(fill=tk.X, padx=10, pady=5)

    tk.Scale(
        root,
        variable=db_var,
        from_=5,
        to=200,
        resolution=1,
        label="Debounce ms",
        orient=tk.HORIZONTAL,
    ).pack(fill=tk.X, padx=10, pady=5)

    result: DetectorConfig | None = None

    def _start() -> None:
        nonlocal result
        result = DetectorConfig(
            upper_offset=u_var.get(),
            lower_offset=l_var.get(),
            samplerate=sr_var.get(),
            blocksize=bs_var.get(),
            debounce_ms=db_var.get(),
        )
        root.destroy()

    tk.Button(root, text="Start", command=_start).pack(pady=10)
    root.mainloop()

    assert result is not None
    return result
