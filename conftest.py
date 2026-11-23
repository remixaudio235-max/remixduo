"""Deterministic offscreen GUI inputs; never borrow a user's live session Fs.

Core resolver tests still call the real smaart_fs_sync_v841 implementation.
Tests exercising GUI invalidation can override the GUI reader per test.
"""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import pytest

# Historical operator probes were named ``test_*.py`` but are not tests: they
# restore/scroll Smaart or open/terminate foreign applications at import time.
# A release regression run must be deterministic and must never operate the
# user's live Smaart session during pytest collection.
collect_ignore = [
    "test_hide_other_window_v7.py",
    "test_live_sync_probe.py",
    "test_uia_scroll_restore.py",
]


@pytest.fixture(autouse=True)
def offline_gui_saved_fs(monkeypatch,tmp_path,request):
    from pathlib import Path
    if Path(request.path).is_relative_to(Path(__file__).parent/'tests'):
        return  # Canonical suites must not import the legacy Windows GUI.
    import signal_tools_gui_v813 as gui
    from smaart_fs_sync_v841 import read_saved_smaart_fs
    folder=tmp_path/'mock_gui_session'; folder.mkdir()
    config=folder/'SmaartConfig.xml'
    config.write_text(
        '<Root><Smaart-Config><Global><SampleRate>48000</SampleRate></Global>'
        '<Sources><Source1><SampleRate>48000</SampleRate></Source1></Sources>'
        '<Dests><Dest1><SampleRate>48000</SampleRate></Dest1></Dests>'
        '</Smaart-Config></Root>',encoding='utf-8')
    monkeypatch.setattr(gui,'read_saved_smaart_fs',
                        lambda path=None:read_saved_smaart_fs(config if path is None else path))
