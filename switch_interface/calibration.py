from dataclasses import dataclass
import tkinter as tk

@dataclass
class DetectorConfig:
    upper_offset: float = -0.2
    lower_offset: float = -0.5
    samplerate: int = 44_100
    blocksize: int = 256
    debounce_ms: int = 40


def calibrate(config: DetectorConfig | None = None) -> DetectorConfig:
    """Launch a simple UI to adjust detector settings."""
    config = config or DetectorConfig()
    root = tk.Tk()
    root.title("Calibrate Detector")

    u_var = tk.DoubleVar(value=config.upper_offset)
    l_var = tk.DoubleVar(value=config.lower_offset)
    sr_var = tk.IntVar(value=config.samplerate)
    bs_var = tk.IntVar(value=config.blocksize)
    db_var = tk.IntVar(value=config.debounce_ms)

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
