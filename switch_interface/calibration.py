import json
import math
import os
import tkinter as tk
from dataclasses import asdict, dataclass
from tkinter import messagebox

import numpy as np
import sounddevice as sd

from .audio.backends.wasapi_backend import get_extra_settings
from .detection import EdgeState, detect_edges


@dataclass
class DetectorConfig:
    upper_offset: float = -0.2
    lower_offset: float = -0.5
    samplerate: int = 44_100
    blocksize: int = 256
    debounce_ms: int = 40
    device: str | None = None


CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".switch_interface")
CONFIG_FILE = os.path.join(CONFIG_DIR, "detector.json")

# --- UI constants ---------------------------------------------------------
CANVAS_WIDTH = 500
CANVAS_HEIGHT = 150
UPDATE_INTERVAL_MS = 30
HIGHLIGHT_MS = 150
PRESS_MARKER_DECAY = 10
BIAS_ALPHA = 0.005
RULER_AMPLITUDES = (1, 0.5, 0, -0.5, -1)

STANDARD_RATES = [8000, 16000, 22050, 32000, 44100, 48000, 88200, 96000]
STANDARD_BLOCKS = [64, 128, 256, 512, 1024, 2048]


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
    db_var = tk.IntVar(master=root, value=config.debounce_ms)
    dev_var = tk.StringVar(master=root, value=config.device or "")

    sr_var = tk.IntVar(master=root, value=config.samplerate)
    bs_var = tk.IntVar(master=root, value=config.blocksize)

    def _add_scale(var, from_: float, to: float, resolution: float, label: str) -> None:
        tk.Scale(
            root,
            variable=var,
            from_=from_,
            to=to,
            resolution=resolution,
            label=label,
            orient=tk.HORIZONTAL,
        ).pack(fill=tk.X, padx=10, pady=5)

    def _supported(param: str, values: list[int], **base: int | str) -> list[int]:
        valid: list[int] = []
        for val in values:
            kw = {
                "samplerate": sr_var.get(),
                "blocksize": bs_var.get(),
                "device": dev_var.get() or None,
                "channels": 1,
                "dtype": "float32",
                **base,
            }
            kw[param] = val
            try:
                sd.check_input_settings(**kw)
            except Exception:
                continue
            valid.append(val)
        return valid or values

    def _valid_rates() -> list[int]:
        return _supported("samplerate", STANDARD_RATES)

    def _valid_blocks() -> list[int]:
        return _supported("blocksize", STANDARD_BLOCKS)

    tk.Label(root, text="Sample rate").pack(padx=10, pady=(10, 0))
    _rates = _valid_rates()
    if sr_var.get() not in _rates:
        sr_var.set(_rates[0])
    sr_menu = tk.OptionMenu(root, sr_var, *_rates)
    sr_menu.pack(fill=tk.X, padx=10)

    tk.Label(root, text="Block size").pack(padx=10, pady=(10, 0))
    _blocks = _valid_blocks()
    if bs_var.get() not in _blocks:
        bs_var.set(_blocks[0])
    bs_menu = tk.OptionMenu(root, bs_var, *_blocks)
    bs_menu.pack(fill=tk.X, padx=10)

    wave_canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white")
    wave_canvas.pack(padx=10, pady=5)

    WIDTH = CANVAS_WIDTH
    HEIGHT = CANVAS_HEIGHT

    def _draw_ruler() -> None:
        for amp in RULER_AMPLITUDES:
            y = HEIGHT / 2 - amp * (HEIGHT / 2)
            wave_canvas.create_line(0, y, WIDTH, y, fill="#ccc", tags="ruler")

    _draw_ruler()

    thr_label = tk.Label(root, text="")
    thr_label.pack(padx=10, pady=(0, 5))

    _add_scale(u_var, -1.0, 1.0, 0.01, "Upper offset")

    _add_scale(l_var, -1.0, 0.0, 0.01, "Lower offset")

    _add_scale(db_var, 5, 200, 1, "Debounce ms")

    devices = [d for d in sd.query_devices() if d.get("max_input_channels", 0) > 0]
    if devices and not dev_var.get():
        dev_var.set(devices[0]["name"])
    tk.Label(root, text="Microphone").pack(padx=10, pady=(10, 0))
    tk.OptionMenu(root, dev_var, *[d["name"] for d in devices]).pack(fill=tk.X, padx=10)

    result: DetectorConfig | None = None
    buf = np.zeros(sr_var.get() * 2, dtype=np.float32)
    buf_index = 0
    bias = 0.0
    stream: sd.InputStream | None = None
    edge_state = EdgeState(armed=True, cooldown=0)
    press_pending = False
    press_marker_x: float | None = None
    press_marker_counter = 0
    normal_bg = root.cget("bg")

    def _stop_stream() -> None:
        nonlocal stream
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
            stream = None

    def _callback(indata: np.ndarray, frames: int, time: int, status: int) -> None:
        nonlocal buf_index, edge_state, press_pending, press_marker_x, press_marker_counter
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
        n = len(mono)
        if n > len(buf):
            mono = mono[-len(buf) :]
            n = len(buf)
        end = buf_index + n
        if end <= len(buf):
            buf[buf_index:end] = mono
        else:
            first = len(buf) - buf_index
            buf[buf_index:] = mono[:first]
            buf[: n - first] = mono[first:]
        buf_index = (buf_index + n) % len(buf)
        refract = int(math.ceil((db_var.get() / 1000) * sr_var.get()))
        start_index = buf_index
        edge_state, pressed, press_idx = detect_edges(
            mono,
            edge_state,
            u_var.get(),
            l_var.get(),
            refract,
        )
        if pressed:
            press_pending = True
            if press_idx is not None:
                idx_global = (start_index + press_idx) % len(buf)
                if idx_global >= buf_index:
                    rel = idx_global - buf_index
                else:
                    rel = len(buf) - (buf_index - idx_global)
                press_marker_x = rel / len(buf) * WIDTH
                press_marker_counter = PRESS_MARKER_DECAY

    def _start_stream() -> None:
        nonlocal stream
        extra = get_extra_settings()
        kwargs = dict(
            samplerate=sr_var.get(),
            blocksize=bs_var.get(),
            channels=1,
            dtype="float32",
            callback=_callback,
            device=dev_var.get() or None,
        )
        if extra is not None:
            kwargs["extra_settings"] = extra
        try:
            stream = sd.InputStream(**kwargs)
        except sd.PortAudioError as exc:
            if extra is not None:
                kwargs.pop("extra_settings", None)
                try:
                    stream = sd.InputStream(**kwargs)
                except sd.PortAudioError as exc2:
                    raise RuntimeError("Failed to open audio input device") from exc2
            else:
                raise RuntimeError("Failed to open audio input device") from exc
        stream.start()

    def _restart_stream() -> None:
        _stop_stream()
        _start_stream()

    def _update_wave() -> None:
        wave_canvas.delete("all")
        _draw_ruler()
        data = np.concatenate([buf[buf_index:], buf[:buf_index]])
        nonlocal bias
        bias = (1 - BIAS_ALPHA) * bias + BIAS_ALPHA * float(data.mean())
        step = max(1, len(data) // WIDTH)
        if step > 1:
            trimmed = data[: step * WIDTH]
        else:
            trimmed = data
        samples = trimmed.reshape(-1, step).mean(axis=1)
        points: list[float] = []
        x_positions = np.linspace(0, WIDTH, len(samples), endpoint=False)
        for x, sample in zip(x_positions, samples):
            y = HEIGHT / 2 - sample * (HEIGHT / 2)
            points.extend([x, y])
        wave_canvas.create_line(*points, fill="blue", tags="wave")
        # dynamic threshold lines
        upper = bias + u_var.get()
        lower = bias + l_var.get()
        thr_label.config(text=f"Upper: {upper:.2f}  Lower: {lower:.2f}")
        y_upper = HEIGHT / 2 - upper * (HEIGHT / 2)
        y_lower = HEIGHT / 2 - lower * (HEIGHT / 2)
        wave_canvas.create_line(0, y_upper, WIDTH, y_upper, fill="red", tags="thr")
        wave_canvas.create_line(0, y_lower, WIDTH, y_lower, fill="red", tags="thr")
        nonlocal press_pending, press_marker_counter
        if press_pending:
            root.configure(bg="yellow")
            root.after(HIGHLIGHT_MS, lambda: root.configure(bg=normal_bg))
            press_pending = False
        if press_marker_counter > 0 and press_marker_x is not None:
            wave_canvas.create_line(
                press_marker_x,
                0,
                press_marker_x,
                HEIGHT,
                fill="orange",
                tags="press",
            )
            press_marker_counter -= 1
        root.after(UPDATE_INTERVAL_MS, _update_wave)

    def _start() -> None:
        nonlocal result
        result = DetectorConfig(
            upper_offset=u_var.get(),
            lower_offset=l_var.get(),
            samplerate=sr_var.get(),
            blocksize=bs_var.get(),
            debounce_ms=db_var.get(),
            device=dev_var.get() or None,
        )
        _stop_stream()
        root.destroy()

    controls = tk.Frame(root)
    controls.pack(pady=10)
    tk.Button(controls, text="Start", command=_start_stream).pack(side=tk.LEFT, padx=5)
    tk.Button(controls, text="Stop", command=_stop_stream).pack(side=tk.LEFT, padx=5)
    tk.Button(controls, text="Save", command=_start).pack(side=tk.LEFT, padx=5)

    def _on_close() -> None:
        _stop_stream()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    try:
        _start_stream()
    except RuntimeError:
        root.withdraw()
        messagebox.showerror(
            "Error",
            "Could not read switch",
            parent=root,
        )
        root.destroy()
        return config

    _update_wave()
    root.mainloop()

    assert result is not None
    return result
