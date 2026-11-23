"""V8.47: NO_EQ_NEEDED is BYPASS, verified MagEQ still follows native pixels.

Regression: Smaart's own blue 4,8 ms delay-1 polyline matched at score
1.00 while the alternative-fit 0.864 just missed legacy 0.14 margin.
Accept ONLY if independently verified native Y grid corroborates, never
accept weak or multiple colors. No Smaart writes.
"""
import time
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication
from smaart_native_mag_fit import NativeMagFit
from trf_core import read_trf
from mageq_trace_v07 import create_mageq_trace
from native_eq_mag_v06 import build_state,native_fit_worker,FitFrame
import native_eq_mag_v06 as native
from remix_autoeq_v05_adapter import RemixEQResult
from overlay_v7 import App,SumGraph
from signal_tools_gui_v813 import ToolHub
from qa_fake_single import FakeSingle
from pathlib import Path

ROOT=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
PLOT=(252,539,1442,412)
WINDOW=(0,0,1920,1040)


def model():
    path=ROOT/"4,8 ms delay-1.trf"
    if not path.exists():pytest.skip("Real read-only TRF unavailable")
    tf=read_trf(path)
    src=build_state(tf.hz,tf.h,tf.coherence,(),fs=48000,
                    source_index=0,source_name=path.stem,
                    revision=47,allow_bypass=True)
    return path,tf,src


def test_zero_eq_requires_explicit_bypass_and_is_identical_mag():
    path,tf,src=model()
    with pytest.raises(ValueError,match="valid PEQ"):
        create_mageq_trace(tf.hz,tf.h,tf.coherence,(),
                           fs=48000,source_index=0,source_name=path.stem,revision=1)
    assert src.peqs==()
    assert np.array_equal(src.original_db,src.after_db)
    assert not src.after_db.flags.writeable
    assert src.source_name==path.stem


def setup_native(monkeypatch,grid_ok=True,multiple=False,score=1.0):
    monkeypatch.setattr(native.win32gui,"IsWindow",lambda h:True)
    monkeypatch.setattr(native.win32gui,"IsIconic",lambda h:False)
    monkeypatch.setattr(native,"locate_role_plots",
                        lambda h:SimpleNamespace(phase=(252,84,1442,412),mag=PLOT))
    monkeypatch.setattr(native,"capture_native_window",
                        lambda h:(Image.new("RGB",(1920,1040),"black"),WINDOW))
    monkeypatch.setattr(native,"detect_magnitude_rect",lambda *a:(PLOT,1.))
    monkeypatch.setattr(native,"choose_color_fit",lambda *a:None)
    monkeypatch.setattr(native,"saved_mag_grid_interval",lambda:3.)
    monkeypatch.setattr(native,"fit_native_mag_grid",lambda *a:SimpleNamespace(
                        accepted=grid_ok,confidence=1.0 if grid_ok else .1,
                        px_per_db=11.5))
    def candidates(*a,trace_color=None,**k):
        if trace_color=="blue" or (multiple and trace_color=="red"):
            return NativeMagFit(170,11.027,-2.,score,.864,221,False,"alt")
        return NativeMagFit(0,0,0,0,0,0,False,"no native")
    monkeypatch.setattr(native,"fit_native_mag",candidates)


def test_strong_original_pixels_and_same_snapshot_grid_rescue(monkeypatch):
    _,_,src=model()
    setup_native(monkeypatch)
    frame=native_fit_worker(77,src)
    assert frame and frame.identity_verified and frame.grid_agrees
    assert frame.source_identity==src.source_identity
    assert frame.color=="blue"
    assert frame.fit.score==1.
    assert abs(frame.fit.px_per_db-11.027)<1e-6


@pytest.mark.parametrize("grid_ok,multiple,score",[
    (False,False,1.),(True,True,1.),(True,False,.80)
])
def test_no_grid_or_weak_or_ambiguous_multicolor_never_unlocks(
        monkeypatch,grid_ok,multiple,score):
    _,_,src=model()
    setup_native(monkeypatch,grid_ok,multiple,score)
    assert native_fit_worker(77,src) is None


def test_bypass_paint_has_zero_markers_and_gradients():
    app=QApplication.instance() or QApplication([])
    _,_,src=model()
    fit=NativeMagFit(170,11.5,-2.,1.0,.86,221,True,"pixel and grid")
    frame=FitFrame(src.revision,PLOT,fit,"blue",time.monotonic(),77,WINDOW,
                   source_identity=src.source_identity,
                   identity_verified=True,grid_agrees=True)
    graph=SumGraph("mag")
    graph.setGeometry(*PLOT)
    graph.set_mageq(src,frame)
    graph.show()
    app.processEvents()
    try:
        graph.grab()
        stats=graph.mageq_annotation_stats
        assert stats["markers"]==0 and stats["gradients"]==0
        assert stats["total_peq"]==0
        assert graph.mageq_draw_count>0
    finally:
        graph.close()


def test_gui_no_eq_needed_publishes_bypass_not_export(monkeypatch):
    from smaart_fs_sync_v841 import SavedSmaartFs
    monkeypatch.setattr('signal_tools_gui_v813.read_saved_smaart_fs',
                        lambda:SavedSmaartFs(48000,1,1,'fixture Suite9'))
    app=QApplication.instance() or QApplication([])
    path,tf,_=model()
    engine=App(False);engine.timer.stop()
    engine.observer=FakeSingle(path)
    engine.current_pair=None
    engine.current_traces=None
    hub=ToolHub(engine)
    hub.timer.stop();hub.native_eq.timer.stop()
    hub.native_fir.timer.stop()
    def no_eq(*a,**kwargs):
        freq=np.asarray(a[0],dtype=float)
        x=np.zeros_like(freq)
        return RemixEQResult(freq,x,x,x,(),2.25,2.25,
                             "NO_EQ_NEEDED",48000,path.stem,())
    monkeypatch.setattr("signal_tools_gui_v813.design_remix_eq",no_eq)
    try:
        hub.select("eq")
        hub.eq.compute()
        limit=time.monotonic()+8
        while hub.eq.result is None and time.monotonic()<limit:
            app.processEvents()
            time.sleep(.012)
        assert hub.eq.result is not None
        assert hub.eq.result.status=="NO_EQ_NEEDED"
        assert hub.native_eq.source is not None
        assert hub.native_eq.source.peqs==()
        assert hub.native_eq.source.source_name==path.stem
        assert hub.native_eq.approved_token==hub.eq._export_source_token
        assert not hub.eq.export.isEnabled()
        assert hub.eq._export_snapshot is None
        assert "BYPASS" in hub.eq.summary.text()
    finally:
        hub.close();app.processEvents()



def test_verified_color_fast_lane_rechecks_native_pixels(monkeypatch):
    _,_,src=model()
    setup_native(monkeypatch)
    import native_eq_mag_v06 as n
    colors=[]
    original=n.fit_native_mag
    def counted(*a,trace_color=None,**kw):
        colors.append(trace_color)
        return original(*a,trace_color=trace_color,**kw)
    monkeypatch.setattr(n,"fit_native_mag",counted)
    frame=n.native_fit_worker(77,src,preferred_color="blue")
    assert frame and frame.identity_verified and frame.color=="blue"
    assert colors==["blue"]
    colors.clear()
    frame=n.native_fit_worker(77,src,preferred_color="red")
    assert frame is None and colors==["red"]


def test_live_same_source_warm_fit_not_stale(monkeypatch):
    # Pure mock confirms the fast lane cannot silently accept an
    # outdated grid even if previous source color is remembered.
    _,_,src=model()
    setup_native(monkeypatch,grid_ok=False)
    import native_eq_mag_v06 as n
    assert n.native_fit_worker(77,src,preferred_color="blue") is None
