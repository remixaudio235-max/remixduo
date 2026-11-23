from pathlib import Path
from unittest.mock import patch
from smaart_runtime_paths_v868 import trace_directory,saved_config
from smaart_smooth_sync_v811 import read_saved_smooth

def test_independent_version_sources():
    home=Path("C:/Admin")
    v8=trace_directory(8,home).as_posix()
    v9=trace_directory(9,home).as_posix()
    assert "Smaart v8" in v8
    assert "Smaart Suite" in v9
    assert v8!=v9
    assert "Smaart v8" in saved_config(8,home).as_posix()
    assert trace_directory(7,home) is None

def test_v8_smoothing_hold_until_calibrated():
    with patch("smaart_runtime_paths_v868.running_major",return_value=8):
        assert read_saved_smooth() is None
