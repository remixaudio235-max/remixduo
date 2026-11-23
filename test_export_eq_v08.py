# -*- coding: utf-8 -*-
"""V0.8 acceptance: new EQ table adjacent to Auto EQ, TXT/PNG, source safety."""
import os,time,hashlib
os.environ["QT_QPA_PLATFORM"]="offscreen"
from pathlib import Path
import pytest
from PyQt6.QtWidgets import QApplication,QHBoxLayout
from autoeq_export_dialog_v08 import EQExportDialog,EQExportSnapshot
from remix_autoeq_v05_adapter import design_remix_eq
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from trf_core import read_trf
from qa_fake_single import FakeSingle
from test_v845_fir_one_trace import wait_fs

DATA=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"

def real_solution():
    p=DATA/"4,8 ms delay-1.trf"
    if not p.exists():pytest.skip("Smaart read-only fixture unavailable")
    tr=read_trf(p)
    r=design_remix_eq(tr.hz,tr.h,tr.coherence,fs=48000,target="House",
          filters=8,lf=60,hf=8000,boost=2,cut=-9,source=p.stem)
    assert r.status=="PREVIEW_READY" and 1<=len(r.peqs)<=8
    assert all(3.<=b.q<=8. for b in r.peqs)
    return p,r

def test_snapshot_exact_order_and_refuse_invalid():
    _,r=real_solution()
    s=EQExportSnapshot.from_result(r,"House")
    assert s.source==r.source and s.fs==r.fs
    assert len(s.rows)==len(r.peqs)
    assert tuple(round(x.hz,3) for x in s.rows)==tuple(round(x.freq_hz,3) for x in r.peqs)
    assert tuple(round(x.q,3) for x in s.rows)==tuple(round(x.q,3) for x in r.peqs)
    assert tuple(x.number for x in s.rows)==tuple(range(1,len(r.peqs)+1))
    import dataclasses
    with pytest.raises(dataclasses.FrozenInstanceError):s.source="other"
    with pytest.raises(ValueError,match="kết quả"):
        EQExportSnapshot.from_result(None,"House")

def test_exports_png_txt_do_not_change_trf(tmp_path):
    path,r=real_solution()
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    app=QApplication.instance() or QApplication([])
    snapshot=EQExportSnapshot.from_result(r,"House")
    txt=tmp_path/"auto_eq.txt"
    png=tmp_path/"auto_eq.png"
    snapshot.save_txt(txt)
    snapshot.save_png(png)
    lines=txt.read_text(encoding="utf-8").splitlines()
    assert lines[6]=="EQ#,Hz,dB,Q"
    assert len(lines)==7+len(r.peqs)
    for i,band in enumerate(r.peqs,1):
        assert lines[6+i]==f"{i},{band.freq_hz:.1f},{band.gain_db:+.2f},{band.q:.2f}"
    assert "KHONG GHI DSP" in txt.read_text(encoding="utf-8")
    assert png.read_bytes()[:8]==b"\x89PNG\r\n\x1a\n"
    from PyQt6.QtGui import QImage
    im=QImage(str(png))
    assert not im.isNull() and im.width()==775 and im.height()==750
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
    with pytest.raises(ValueError):snapshot.save_txt(tmp_path/"bad.trf")

def test_12x4_table_and_export_actions(tmp_path):
    app=QApplication.instance() or QApplication([])
    _,r=real_solution()
    snap=EQExportSnapshot.from_result(r,"House")
    dlg=EQExportDialog(snap)
    try:
        assert dlg.table.rowCount()==12
        assert dlg.table.columnCount()==4
        assert [dlg.table.horizontalHeaderItem(i).text() for i in range(4)]==["EQ#","Hz","dB","Q"]
        for i,band in enumerate(r.peqs):
            assert dlg.table.item(i,0).text()==f"EQ{i+1}"
            assert dlg.table.item(i,1).text()==f"{band.freq_hz:.1f}"
            assert dlg.table.item(i,2).text()==f"{band.gain_db:+.2f}"
            assert dlg.table.item(i,3).text()==f"{band.q:.2f}"
        assert dlg.table.item(11,1).text()=="—"
        assert dlg.txt_button.text()=="Lưu TXT"
        assert dlg.png_button.text()=="Lưu PNG"
    finally:dlg.close();app.processEvents()

def test_gui_adjacent_export_and_exact_latest_result(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    path,_=real_solution()
    other=DATA/"0 delay-1.trf"
    engine=App(False);engine.timer.stop()
    traces=(read_trf(path),read_trf(other))
    engine.current_traces=traces
    engine.current_pair=tuple(str(t.path) for t in traces)
    engine.observer=FakeSingle(path)  # One independently verified EQ trace
    original_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    hub=ToolHub(engine);hub.timer.stop();hub.native_eq.timer.stop()
    try:
        hub.select("eq");app.processEvents()
        wait_fs(app,hub)
        eq=hub.eq
        assert eq.calculate.text()=="AUTO EQ"
        assert eq.export.text()=="Xuất EQ"
        layout=eq.calculate.parentWidget().layout()
        # Adjacent in the same action row, not in a separate mini-plot or tab.
        rows=[v for v in eq.main.findChildren(QHBoxLayout) if
              v.indexOf(eq.calculate)>=0]
        assert rows and rows[0].itemAt(1).widget() is eq.export
        assert not eq.export.isEnabled()
        assert eq.fs.currentData()==48000
        assert not eq.fs.isEnabled()
        eq.source.setCurrentIndex(0)
        eq.target.setCurrentIndex(eq.target.findData("House"))
        eq.compute()
        deadline=time.monotonic()+12
        while eq.result is None and time.monotonic()<deadline:
            app.processEvents();time.sleep(.01)
        assert eq.result is not None
        assert not eq.export.isEnabled()
        assert eq._export_snapshot is not None
        assert not eq._native_export_ok()
        assert eq._export_dialog is None
        # Synthetic verified pixel frame: only a real native match may enable it.
        import native_eq_mag_v06 as native
        from smaart_native_mag_fit import NativeMagFit
        src=hub.native_eq.source
        assert src is not None
        assert hub.native_eq.approved_token==eq._export_source_token
        hub.native_eq.frame=native.FitFrame(
            src.revision,(252,539,1442,412),
            NativeMagFit(171.,11.5,0.,.94,0.,150,True,"QA match"),
            "red",time.monotonic(),123,(0,0,1920,1080),
            source_identity=src.source_identity,identity_verified=True)
        monkeypatch.setattr(native,"frame_is_fresh_for_window",
                            lambda frame,hwnd:True)
        eq._refresh_export_gate()
        assert eq.export.isEnabled()
        eq.export.click();app.processEvents()
        assert eq._export_dialog is not None
        assert eq._export_dialog.isVisible()
        assert len(eq._export_dialog.snapshot.rows)==len(eq.result.peqs)
        assert hub.native_eq.source is not None
        assert eq.plot.isHidden()
        # A recalculation or different source invalidates export immediately.
        eq.target.setCurrentIndex(eq.target.findData("Flat"))
        app.processEvents()
        assert eq.result is None and not eq.export.isEnabled()
        assert eq._export_snapshot is None
        assert eq._export_dialog is None or not eq._export_dialog.isVisible()
        assert hub.native_eq.source is None
        assert hashlib.sha256(path.read_bytes()).hexdigest()==original_sha
    finally:hub.close();app.processEvents()

def test_top_bar_export_is_adjacent_and_opens_same_latest_table():
    app=QApplication.instance() or QApplication([])
    path,_=real_solution()
    other=DATA/"0 delay-1.trf"
    engine=App(False);engine.timer.stop()
    engine.current_traces=(read_trf(path),read_trf(other))
    engine.current_pair=(str(path),str(other))
    engine.observer=FakeSingle(path)  # One independently verified EQ trace
    hub=ToolHub(engine);hub.timer.stop();hub.native_eq.timer.stop()
    try:
        assert tuple(hub.buttons.keys())==("phase","eq","fir")
        assert hub.eq.export.text()=="Xuất EQ"
        assert not hub.eq.export.isEnabled()
        assert hub.nav_frame.height()==30  # V8.17 native Smaart top-row parity
        assert hub.width()==205
        hub.select("eq")
        wait_fs(app,hub)
        assert hub.eq.fs.currentData()==48000
        assert not hub.eq.fs.isEnabled()
        hub.eq.target.setCurrentIndex(hub.eq.target.findData("House"))
        hub.eq.source.setCurrentIndex(0)
        hub.eq.compute()
        deadline=time.monotonic()+14
        while hub.eq.result is None and time.monotonic()<deadline:
            app.processEvents();time.sleep(.01)
        assert hub.eq.result is not None
        assert not hub.eq.export.isEnabled()
        hub.eq.export.click()
        app.processEvents()
        assert hub.active=="eq" and hub.dock.stack.currentWidget()==hub.eq
        assert hub.eq._export_dialog is None
        # The original trace and MagEq remain independently present.
        assert hub.native_eq.source is not None
        assert hub.eq.plot.isHidden()
        hub.eq.target.setCurrentIndex(hub.eq.target.findData("Flat"))
        app.processEvents()
        assert not hub.eq.export.isEnabled()
    finally:
        hub.close();app.processEvents()
