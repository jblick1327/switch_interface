from switch_interface.calibration import DetectorConfig, save_config, load_config


def test_save_and_load(tmp_path):
    cfg = DetectorConfig(upper_offset=-0.1, lower_offset=-0.6, samplerate=8000, blocksize=128, debounce_ms=50)
    path = tmp_path / "detector.json"
    save_config(cfg, path=str(path))
    loaded = load_config(path=str(path))
    assert loaded == cfg
