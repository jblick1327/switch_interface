import types
import sys
import numpy as np
import pytest

# Provide a dummy sounddevice module so detection imports succeed
sd_mod = types.SimpleNamespace(
    WasapiSettings=lambda exclusive=True: None,
    query_hostapis=lambda idx: {"name": "Other"},
    default=types.SimpleNamespace(hostapi=0),
)
sys.modules.setdefault("sounddevice", sd_mod)

from switch_interface.detection import detect_edges, EdgeState


def test_detect_edges_requires_1d():
    state = EdgeState(armed=True, cooldown=0)
    block = np.zeros((2, 2))
    with pytest.raises(ValueError) as excinfo:
        detect_edges(block, state, -0.2, -0.5, 1)
    assert "block must be a 1-D array" in str(excinfo.value)
    assert "(2, 2)" in str(excinfo.value)
