"""V8.107: one incomplete Data Bar scan must not blink SUM / MagEQ / FIR.

Root cause: a single transient scan (scroll during capture, ambiguous
visible tick, PrintWindow read error) resets the 3/3 tick lock. Re-arming
needs three fresh polls (~0.6-1.2 s live), but presentation was tied to
the strict lock with a display grace of 0 s (SUM, FIR) or 0.44 s (MagEQ).

Contract kept: the bridge is DISPLAY-ONLY and bounded; a complete scan
that contradicts the committed source (other pair, count != 2 / != 1,
different candidate) still hides immediately; Solve / Auto EQ / Export
remain strictly gated by a fresh 3/3 lock.
"""
from __future__ import annotations
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import time
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from PyQt6.QtWidgets import QApplication

from mageq_presentation_gate_v853 import (
    TRANSIENT_DISPLAY_GRACE_S,presentation_tick_ok)
from live_sync_v7 import SyncResult
from trf_core import Candidate

POLL_S=0.30          # measured live poll cadence upper range (PrintWindow+parse)


def test_display_grace_covers_one_transient_plus_full_rearm_but_is_bounded():
    # one failed poll + three fresh polls for 3/3, plus scheduling slack
    assert TRANSIENT_DISPLAY_GRACE_S>=4*POLL_S
    # never longer than the observer's own 1.5 s row-freshness proof
    assert TRANSIENT_DISPLAY_GRACE_S<=1.5


class Observer:
    def __init__(self,token):
        self.single_tick=token
        self.single_candidate=token[:3]
        self.ready=True
        self.order=[token[0]]
        self.states={0:"on"}
    def current_single(self):
        return self.single_tick


def test_eq_rearm_after_one_transient_keeps_display():
    token=("c:/a.trf",1,2,3)
    o=Observer(token)
    ok,at,_=presentation_tick_ok(o,token,0.,now=50.)
    assert ok
    o.single_tick=None            # suspend_single_transient()
    for k in range(1,5):          # transient + 3 re-arm polls
        ok,_,reason=presentation_tick_ok(o,token,at,now=50.+k*POLL_S)
        assert ok,(k,reason)
    o.states={0:"off"}            # complete scan: tick removed -> hard stop
    ok,_,_=presentation_tick_ok(o,token,at,now=50.+POLL_S)
    assert not ok


# ---------------------------------------------------------------- SUM ----
@pytest.fixture
def engine(monkeypatch):
    import overlay_v7 as gui
    import signal_tools_gui_v813 as tools
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(tools,"show_notice",lambda *a,**k:None)
    e=gui.App(demo=True);e.timer.stop();e.drag_timer.stop()
    # Live transient results carry active_names=None; found() then reads the
    # observer's cached map (unknown rows => ambiguous).
    e.observer=NS(states={0:"on",1:"unknown"},order=["c:/a.trf","c:/b.trf"])
    # Patch methods on the real controller (replacing the object would
    # orphan its demo loader thread and crash Qt at teardown).
    ctl=e.controller
    monkeypatch.setattr(ctl,"apply",lambda pair,why:setattr(ctl,"last_pair",pair),
                        raising=False)
    monkeypatch.setattr(ctl,"invalidate",lambda why:setattr(ctl,"last_pair",None),
                        raising=False)
    ctl.last_pair=None
    clock={"t":1000.}
    monkeypatch.setattr(gui,"_selection_now",lambda:clock["t"])
    e._clock=clock
    yield e
    e.close();app.processEvents()


PAIR=("c:/a.trf","c:/b.trf")


def ok_scan():
    return SyncResult(PAIR,"Verified viewport 6 rows; cached 6/6 rows, active 2",
                      6,6,False,0.,PAIR,0)


def transient_scan():
    return SyncResult(None,"Scroll changed during capture; unverified",0,6,True,0.)


def commit(engine):
    for _ in range(3):
        engine._clock["t"]+=POLL_S
        engine.found(ok_scan())
    assert engine._selection_verified
    # A real Auto Phase candidate is required: the GUI re-renders Top-3
    # on tick recovery, and a placeholder string cannot be routed safely.
    engine.last_solve=[Candidate(1.0,False,-1.0,100)]


def test_sum_survives_one_transient_scan_and_rearm(engine):
    commit(engine)
    steps=[transient_scan(),ok_scan(),ok_scan(),ok_scan()]
    for result in steps:
        engine._clock["t"]+=POLL_S
        engine.found(result)
        assert engine._selection_verified, "SUM hidden during a bounded re-arm"
    assert engine.last_solve==[Candidate(1.0,False,-1.0,100)]


def test_sum_hold_never_enables_solve(engine):
    commit(engine)
    engine.current_traces=(object(),object())
    engine._clock["t"]+=POLL_S
    engine.found(transient_scan())
    assert engine._selection_verified
    assert not engine.solve.isEnabled()


def test_sum_hold_is_bounded(engine):
    commit(engine)
    engine._clock["t"]+=POLL_S
    engine.found(transient_scan())
    assert engine._selection_verified
    engine._clock["t"]+=TRANSIENT_DISPLAY_GRACE_S+.01
    engine.found(transient_scan())
    assert not engine._selection_verified
    assert engine.last_solve is None


@pytest.mark.parametrize("contradiction",["count3","other_pair"])
def test_sum_complete_contradiction_hides_immediately(engine,contradiction):
    commit(engine)
    engine._clock["t"]+=POLL_S
    if contradiction=="count3":
        names=PAIR+("c:/c.trf",)
        r=SyncResult(None,"Verified viewport 6 rows; cached 6/6 rows, active 3",
                     6,6,True,0.,names,0)
        engine.found(r)       # pending 1/3 of a different (invalid) state
    else:
        other=("c:/a.trf","c:/z.trf")
        r=SyncResult(other,"Verified viewport 6 rows; cached 6/6 rows, active 2",
                     6,6,True,0.,other,0)
        engine.found(r)       # pending 1/3 of a DIFFERENT pair
    assert not engine._selection_verified


def test_sum_pair_path_mismatch_hides_immediately(engine):
    commit(engine)
    engine._clock["t"]+=POLL_S
    bad=SyncResult(("c:/x.trf","c:/y.trf"),
                   "Verified viewport 6 rows; cached 6/6 rows, active 2",
                   6,6,True,0.,PAIR,0)
    engine.found(bad)
    assert not engine._selection_verified


# ---------------------------------------------------------------- FIR ----
class W:
    def __init__(self,v):self.v=v
    def currentData(self):return self.v
    def value(self):return self.v
    def isChecked(self):return False


def fir_fake(tmp_path,observer):
    from signal_tools_gui_v813 import FIRDialog
    p=tmp_path/"src.trf";p.write_bytes(b"trf bytes")
    st=p.stat();token=(str(p),st.st_mtime_ns,st.st_size,5)
    snap=NS(hz=48000)
    digest=FIRDialog._source_hash(p)
    observer.single_tick=token;observer.single_candidate=token[:3]
    observer.order=[token[0]];observer.states={0:"on"}
    fake=NS(_approved=(token,digest,snap,1024,30,16000,"mag"),
            result=NS(mode="mag",fs=48000,taps=[0]*1024,source=p.stem),
            _fir_token=token,_fir_fs=snap,
            taps=W(1024),fir_lf=W(30),fir_hf=W(16000),fir_mode=W("mag"),
            phase_plus=W(False),_approved_phase_plus=False,
            engine=NS(observer=observer),_manual_token=None)
    fake._fir_fs_snapshot=lambda:snap
    fake._source_hash=FIRDialog._source_hash
    fake._taps_choice_matches=lambda actual: int(fake.taps.currentData()) in (0,int(actual))
    fake._verified_single=lambda:observer.current_single()
    fake._proof_current=lambda **k:FIRDialog._proof_current(fake,**k)
    return fake,token


def test_fir_display_proof_bridges_rearm_but_export_proof_is_strict(tmp_path):
    o=Observer(("x",0,0,0))
    fake,token=fir_fake(tmp_path,o)
    assert fake._proof_current(display=True)
    assert fake._proof_current()
    o.single_tick=None                 # one transient scan
    fake._fir_token=None               # refresh_sources() transient branch
    assert fake._proof_current(display=True), "FIR curve blinked on re-arm"
    assert not fake._proof_current(), "export must stay strict"


@pytest.mark.parametrize("change",["other_candidate","zero_ticks","expired",
                                   "other_verified"])
def test_fir_display_proof_hard_stops(tmp_path,monkeypatch,change):
    import signal_tools_gui_v813 as tools
    o=Observer(("x",0,0,0))
    fake,token=fir_fake(tmp_path,o)
    assert fake._proof_current(display=True)
    o.single_tick=None;fake._fir_token=None
    if change=="other_candidate":o.single_candidate=("c:/other.trf",1,1)
    if change=="zero_ticks":o.states={0:"off"}
    if change=="other_verified":o.single_tick=("c:/other.trf",1,1,9)
    if change=="expired":
        real=time.perf_counter()
        monkeypatch.setattr(tools,"_fir_display_now",
                            lambda:real+TRANSIENT_DISPLAY_GRACE_S+.05)
    assert not fake._proof_current(display=True)


def test_native_fir_overlay_uses_fresh_native_pixels_not_transient_tick_proof():
    src=Path(__file__).with_name("fir_native_v846.py").read_text(encoding="utf-8")
    allowed=src.split("def _allowed",1)[1].split("def ",1)[0]
    assert "_proof_current(display=True)" not in allowed
    worker=src.split("def native_fir_frame",1)[1].split("def rasterize_fir_frame",1)[0]
    assert "choose_color_fit" in worker
    assert "phase_native_fit" in worker
    assert "detect_magnitude_rect" in worker
