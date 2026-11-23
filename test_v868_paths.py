from pathlib import Path
from unittest.mock import patch
from smaart_runtime_paths_v868 import trace_directory,saved_config
from smaart_smooth_sync_v811 import read_saved_smooth,smoothing_config_path
import smaart_smooth_sync_v811 as smooth

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


def test_suite_smoothing_uses_redirected_known_documents_config(tmp_path,monkeypatch):
    config=tmp_path/"OneDrive"/"Documents"/"Smaart Suite"/"Config"/"SmaartConfig.xml"
    config.parent.mkdir(parents=True)
    config.write_text("""<root>
      <plotProperties><name>Phase1</name><visible>1</visible><smoothingId>4</smoothingId></plotProperties>
      <plotProperties><name>Magnitude1</name><visible>1</visible><smoothingId>4</smoothingId></plotProperties>
    </root>""",encoding="utf-8")
    monkeypatch.setattr("smaart_runtime_paths_v868.running_major",lambda:9)
    monkeypatch.setattr("smaart_runtime_paths_v868.saved_config",lambda major=None:config)
    monkeypatch.setattr(smooth,"CONFIG",tmp_path/"wrong"/"SmaartConfig.xml")
    result=read_saved_smooth()
    assert result is not None and result.mag_id==4 and result.phase_id==4
    assert smoothing_config_path()==config
