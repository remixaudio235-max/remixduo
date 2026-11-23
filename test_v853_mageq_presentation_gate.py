"""V8.53: non-blinking presentation during brief 3/3 rearm, strict export."""
from pathlib import Path
from types import SimpleNamespace as NS
import time
import pytest
from mageq_presentation_gate_v853 import (
    TRANSIENT_DISPLAY_GRACE_S,presentation_tick_ok,
    keep_preview_on_partial_scan)
from native_eq_mag_v06 import NativeAutoEQMag,FitFrame,frame_is_fresh_for_window
from signal_tools_gui_v813 import ToolHub


class Observer:
    def __init__(self,token):
        self.single_tick=token
        self.single_candidate=token[:3]
        self.ready=True
        self.order=[token[0]]
        self.states={0:"on"}

    def current_single(self):
        return self.single_tick


def test_rearm_same_candidate_only_within_short_bounded_grace():
    token=("c:/source.trf",10,123,7)
    o=Observer(token)
    ok,at,reason=presentation_tick_ok(o,token,0,now=100.)
    assert ok and at==100. and reason=="verified_single"
    o.single_tick=None
    for elapsed in (.05,.25,TRANSIENT_DISPLAY_GRACE_S):
        ok,_,reason=presentation_tick_ok(o,token,at,now=100.+elapsed)
        assert ok and reason=="verified_candidate_rearming"
    ok,_,reason=presentation_tick_ok(o,token,at,
                                     now=100.+TRANSIENT_DISPLAY_GRACE_S+.01)
    assert not ok and reason=="candidate_expired"
    # No additional time is granted by repeatedly polling a stale candidate.
    assert at==100.


@pytest.mark.parametrize("change",[
    "new_candidate","no_candidate","verified_other","multiple_ticks",
    "zero_ticks"])
def test_changed_or_ambiguous_source_fails_immediately(change):
    token=("c:/a.trf",10,123,7)
    o=Observer(token)
    o.single_tick=None
    if change=="new_candidate":o.single_candidate=("c:/b.trf",11,456)
    if change=="no_candidate":o.single_candidate=None
    if change=="verified_other":o.single_tick=("c:/b.trf",11,456,8)
    if change=="multiple_ticks":
        o.order=["a","b"];o.states={0:"on",1:"on"}
    if change=="zero_ticks":o.states={0:"off"}
    ok,_,_=presentation_tick_ok(o,token,100.,now=100.01)
    assert not ok


def test_preview_retention_is_not_export_authorization():
    token=("c:/a.trf",10,123,7)
    assert keep_preview_on_partial_scan(None,token,token[:3],None)
    assert keep_preview_on_partial_scan(None,token,None,None)
    assert not keep_preview_on_partial_scan(None,token,("c:/b.trf",9,9),None)
    assert not keep_preview_on_partial_scan(None,token,None,2)
    assert not keep_preview_on_partial_scan(None,token,None,0)
    assert not keep_preview_on_partial_scan(token,token,token[:3],1)


def test_hub_and_native_strict_export_binding_are_separate(tmp_path,monkeypatch):
    p=tmp_path/"a.trf"
    p.write_bytes(b"read only")
    st=p.stat()
    token=(str(p),st.st_mtime_ns,st.st_size,7)
    obs=Observer(token)
    eq=NS(_single_token=token,_export_source_token=token,
          result=object(),_verified_single=obs.current_single)
    hub=NS(engine=NS(observer=obs),eq=eq)
    hub._eq_last_verified_at=0.
    hub._eq_tick_safe=lambda:ToolHub._eq_tick_safe(hub)
    native=NS(source=NS(source_name=p.stem),approved_token=token,hub=hub)
    assert NativeAutoEQMag._source_binding_ok(native)
    assert hub._eq_tick_safe()
    obs.single_tick=None
    assert hub._eq_tick_safe()
    # Native display can bridge this short re-arm, but exporting cannot.
    assert NativeAutoEQMag._source_binding_ok(native,presentation=True)
    assert not NativeAutoEQMag._source_binding_ok(native)
    obs.single_candidate=None
    assert not hub._eq_tick_safe()
    assert not NativeAutoEQMag._source_binding_ok(native,presentation=True)


def test_native_frame_age_and_changed_viewport_still_hard_gated(monkeypatch):
    import native_eq_mag_v06 as native
    now=time.monotonic()
    fit=NS()
    f=FitFrame(3,(252,539,1442,412),fit,"red",now,77,
               (0,0,1920,1040),"unchanged",True,True)
    monkeypatch.setattr(native.win32gui,"IsWindow",lambda h:True)
    monkeypatch.setattr(native.win32gui,"IsIconic",lambda h:False)
    monkeypatch.setattr(native.win32gui,"GetWindowRect",
                        lambda h:(0,0,1920,1040))
    assert frame_is_fresh_for_window(f,77,now=now+.1)
    assert not frame_is_fresh_for_window(f,77,now=now+1.)
    assert not frame_is_fresh_for_window(f,88,now=now+.1)
    monkeypatch.setattr(native.win32gui,"GetWindowRect",
                        lambda h:(0,0,1700,1000))
    assert not frame_is_fresh_for_window(f,77,now=now+.1)


def test_invalid_true_change_must_not_leave_stale_overlay(monkeypatch,tmp_path):
    # Retention is only in EQ preview state; never relax graph
    # source identity, Native Frame proof or Export gate.
    a=tmp_path/"a.trf";a.write_bytes(b"A")
    s=a.stat();token=(str(a),s.st_mtime_ns,s.st_size,7)
    o=Observer(token)
    o.single_tick=None
    o.single_candidate=("other",1,1)
    ok,_,reason=presentation_tick_ok(o,token,100,now=100.1)
    assert not ok
    assert reason=="different_or_unavailable_candidate"


def test_qt_preview_restored_after_partial_scan_same_trace(tmp_path,monkeypatch):
    from PyQt6.QtWidgets import QApplication
    from overlay_v7 import App
    from signal_tools_gui_v813 import EQDialog
    app=QApplication.instance() or QApplication([])
    file=tmp_path/"same.trf"
    file.write_bytes(b"static source")
    st=file.stat()
    token=(str(file),st.st_mtime_ns,st.st_size,9)
    obs=Observer(token)
    obs.single_scan_at=time.perf_counter()
    engine=App(False)
    engine.timer.stop()
    engine.observer=obs
    eq=EQDialog(engine)
    eq._pool.shutdown(wait=False,cancel_futures=True)
    monkeypatch.setattr(eq,"_refresh_fs",lambda *a,**k:None)
    try:
        eq._single_token=token
        eq._eq_state=(token,1)
        eq.source.clear()
        eq.source.addItem("✔ same",0)
        result=object()
        eq.result=result
        obs.single_tick=None
        obs.single_candidate=None
        obs.single_scan_at=0.
        eq.refresh_sources()
        assert eq.result is result
        assert eq.source.currentData() is None
        assert eq._single_token==token
        # Same source is independently accepted again, without a new
        # solver calculation or destroying the original PEQ proposal.
        obs.single_candidate=token[:3]
        obs.single_tick=token
        obs.single_scan_at=time.perf_counter()
        eq.refresh_sources()
        assert eq.result is result
        assert eq.source.currentData()==0
        assert eq._single_token==token
    finally:
        eq.close()
        engine.close()
        app.processEvents()
