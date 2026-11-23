"""V8.41 read-only Smaart Fs auto-sync; no hardware or Smaart mutation."""
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import time
import pytest
from PyQt6.QtWidgets import QApplication

from smaart_fs_sync_v841 import read_saved_smaart_fs
from signal_tools_gui_v813 import EQDialog
from signal_tools_gui_v813 import TFDialog
from overlay_v7 import App


def config(tmp_path,global_fs=48000,source_fs=None,dest_fs=None):
    root=ET.Element("Root")
    smaart=ET.SubElement(root,"Smaart-Config")
    top=ET.SubElement(smaart,"Global")
    ET.SubElement(top,"SampleRate").text=str(global_fs)
    for label,prefix,rate in (
        ("Sources","Source",source_fs if source_fs is not None else global_fs),
        ("Dests","Dest",dest_fs if dest_fs is not None else global_fs)):
        parent=ET.SubElement(smaart,label)
        for n in range(1,3):
            node=ET.SubElement(parent,f"{prefix}{n}")
            ET.SubElement(node,"SampleRate").text=str(rate)
    file=tmp_path/"SmaartConfig.xml"
    ET.ElementTree(root).write(file,encoding="utf-8")
    return file


@pytest.mark.parametrize("rate",[44100,48000,88200,96000,192000])
def test_sync_smaart_global_and_sources_destinations(tmp_path,rate):
    f=config(tmp_path,rate)
    snap=read_saved_smaart_fs(f)
    assert snap and snap.hz==rate
    assert snap.modified_ns==f.stat().st_mtime_ns


@pytest.mark.parametrize("wrong",[
    dict(global_fs=48000,source_fs=96000),
    dict(global_fs=48000,dest_fs=44100),
    dict(global_fs=32000),
])
def test_conflicting_or_unsupported_fs_fails_closed(tmp_path,wrong):
    assert read_saved_smaart_fs(config(tmp_path,**wrong)) is None


def test_corrupt_or_missing_config_fails_closed(tmp_path):
    p=tmp_path/"SmaartConfig.xml"
    assert read_saved_smaart_fs(p) is None
    p.write_text("<Root>",encoding="utf-8")
    assert read_saved_smaart_fs(p) is None


def test_autoeq_fs_field_is_locked_and_initialized(monkeypatch,tmp_path):
    app=QApplication.instance() or QApplication([])
    src=config(tmp_path,48000)
    monkeypatch.setattr("signal_tools_gui_v813.read_saved_smaart_fs",
                        lambda:read_saved_smaart_fs(src))
    engine=App(False)
    engine.timer.stop()
    eq=EQDialog(engine)
    try:
        assert eq.fs.currentData()==48000
        assert not eq.fs.isEnabled()
        assert eq._parameters()["fs"]==48000
        # Rate changed in Smaart's saved config: auto invalidate preview.
        eq.result=object()
        src=config(tmp_path,96000)
        eq._refresh_fs(force=True)
        assert eq.fs.currentData()==96000
        assert eq.result is None
        assert eq._parameters()["fs"]==96000
        src=config(tmp_path,48000,source_fs=96000)
        eq._refresh_fs(force=True)
        assert eq.fs.currentData() is None
        with pytest.raises(ValueError,match="Fs"):
            eq._parameters()
    finally:
        eq._really_close=True
        eq.close()
        engine.close()


def test_saved_fs_uses_observer_edition_when_v8_and_suite_both_run(monkeypatch):
    expected=object();seen=[]
    monkeypatch.setattr("smaart_runtime_paths_v868.running_major",lambda:None)
    monkeypatch.setattr("smaart_runtime_paths_v868.saved_config",
                        lambda edition:seen.append(edition) or Path(f"cfg-{edition}.xml"))
    fake=SimpleNamespace(engine=SimpleNamespace(
        observer=SimpleNamespace(hwnd=0,folder=Path.home()/"Documents"/
                                 "Smaart Suite"/"Data"/"Transfer Function"/
                                 "Session Data"),
        _saved_fs_cache=SimpleNamespace(get=lambda path:expected)))
    assert TFDialog._saved_fs(fake) is expected
    assert seen==[9]
