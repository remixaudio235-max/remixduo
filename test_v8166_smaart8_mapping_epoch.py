"""Smaart 8: consistent index/file map, exactly visible ticks, no false pass."""
import os
from pathlib import Path
from PIL import Image,ImageDraw
import live_sync_v7 as live
from stable_ticks_v824 import StableTickGate
from test_v8121_smaart8_ticks import _observer,FIX,HOST


def test_change_index_during_capture_forces_hold(monkeypatch,tmp_path):
    obs=_observer(monkeypatch,tmp_path,Image.open(FIX))
    index=obs.folder.parent/"index.xml"
    original=live.printwindow_image
    def concurrent_index_edit(hwnd):
        now=index.stat().st_mtime_ns
        os.utime(index,ns=(now+3_000_000_000,now+3_000_000_000))
        return original(hwnd)
    monkeypatch.setattr(live,"printwindow_image",concurrent_index_edit)
    result=obs.poll(77)
    assert result.pair is None
    assert "HOLD" in result.status and "file/index" in result.status
    assert result.source_id==(77,str(obs.folder))
    assert result.frame_id is None
    assert obs.current_single() is None


def test_import_new_trf_during_screenshot_must_not_rebind_icons(monkeypatch,tmp_path):
    obs=_observer(monkeypatch,tmp_path,Image.open(FIX))
    before=live.printwindow_image
    def new_file(hwnd):
        (obs.folder/"unexpected.trf").write_bytes(b"new")
        return before(hwnd)
    monkeypatch.setattr(live,"printwindow_image",new_file)
    result=obs.poll(77)
    assert result.pair is None and "HOLD" in result.status
    assert obs.current_single() is None


def test_valid_smaart8_two_checked_proves_same_frame_mapping(monkeypatch,tmp_path):
    image=Image.open(FIX).convert("RGB")
    draw=ImageDraw.Draw(image)
    # Real fixture contains exactly three archived icons; check one OFF
    # using its same white-X convention.
    draw.line((27,162,40,179),fill=(255,255,255),width=2)
    draw.line((40,162,27,179),fill=(255,255,255),width=2)
    obs=_observer(monkeypatch,tmp_path,image)
    gate=StableTickGate(required=3)
    seen=[]
    for i in range(3):
        r=obs.poll(77)
        d=gate.evaluate(r,r.active_names,r.ambiguous)
        seen.append(d.state)
        assert r.observed_active_names==r.active_names
        assert r.source_id==(77,str(obs.folder))
    assert seen==["pending","pending","valid"]
    assert len(gate.committed)==2
    assert all(Path(x).name.endswith(".trf") for x in gate.committed)
    assert obs.current_single() is None


def test_smaart8_hidden_extra_trace_refuses_2trace(monkeypatch,tmp_path):
    obs=_observer(monkeypatch,tmp_path,Image.open(FIX))
    (obs.folder/"extra.trf").write_bytes(b"x")
    gate=StableTickGate()
    for _ in range(4):
        r=obs.poll(77)
        d=gate.evaluate(r,r.active_names or (),r.ambiguous)
        assert r.pair is None and not r.status.startswith("Verified")
        assert d.state=="transient"
    assert gate.committed is None
