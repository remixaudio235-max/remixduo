from unittest.mock import patch
from live_sync_v7 import LiveDataBarV7

def test_v8_no_legacy_mapping(tmp_path):
    reader=LiveDataBarV7(tmp_path)
    with patch("smaart8_api3_readonly_v868.process_smaart_major",return_value=8):
        result=reader.poll(778)
    assert result.pair is None
    assert reader.current_single() is None
    assert result.verified==0
