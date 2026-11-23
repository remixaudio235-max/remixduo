# -*- coding: utf-8 -*-
"""V8.25 native reader: independent 3/3 single tick vs 3/3 pair."""
import os,time,hashlib
os.environ["QT_QPA_PLATFORM"]="offscreen"
from pathlib import Path
import pytest
from PyQt6.QtWidgets import QApplication
from live_sync_v7 import LiveDataBarV7
from selection_v7 import archive_order
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
DATA=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"

def setup():
    obs=LiveDataBarV7(DATA)
    obs.order=archive_order(DATA)
    assert len(obs.order)>=6
    obs.states={i:"off" for i in range(len(obs.order))}
    obs.ready=True
    return obs

def tick(obs,ids):
    obs.states={i:("on" if i in ids else "off") for i in range(len(obs.order))}
    obs.observe_single(time.perf_counter())

def test_zero_one_two_six_and_independent_autophase_pair():
    obs=setup()
    for ids in [(),(0,1),(0,1,2,3,4,5)]:
        for _ in range(3):tick(obs,ids)
        assert obs.current_single() is None
        if len(ids)==2: assert obs._pair()==(str(obs.order[0]),str(obs.order[1]))
        else: assert obs._pair() is None
    tick(obs,{0})
    assert obs.current_single() is None and obs.single_stable==1
    tick(obs,{0})
    assert obs.current_single() is None and obs.single_stable==2
    tick(obs,{0})
    t=obs.current_single()
    assert t and Path(t[0])==obs.order[0] and len(t)==4
    assert obs._pair() is None  # AutoPhase still requires two ticks.
    tick(obs,{1})
    assert obs.current_single() is None and obs.single_stable==1
    for _ in range(2):tick(obs,{1})
    new=obs.current_single()
    assert new and new[0]==str(obs.order[1]) and new[3]>t[3]
    tick(obs,{0,1})
    assert obs.current_single() is None
    assert obs._pair()==(str(obs.order[0]),str(obs.order[1]))
    tick(obs,())
    assert obs.current_single() is None

def test_expiry_error_and_untrusted_snapshot_do_not_reuse():
    obs=setup()
    for _ in range(3):tick(obs,{0})
    assert obs.current_single()
    obs.single_verified_at=time.perf_counter()-2
    assert obs.current_single() is None
    obs.observe_single(time.perf_counter())
    assert obs.current_single() is not None
    obs.invalidate_single()
    assert obs.current_single() is None
    obs.states[1]="unknown"
    obs.observe_single(time.perf_counter())
    assert obs.current_single() is None
    assert obs.single_stable==0

def test_gui_one_tick_without_autophase_pair_and_safely_clear():
    app=QApplication.instance() or QApplication([])
    obs=setup()
    for _ in range(3):tick(obs,{0})
    engine=App(False)
    engine.timer.stop()
    engine.observer=obs
    engine.current_pair=None
    engine.current_traces=None
    engine._selection_verified=False # AutoPhase pair invalid but EQ one tick valid
    hub=ToolHub(engine);hub.timer.stop();hub.native_eq.timer.stop()
    try:
        hub.select("eq")
        eq=hub.eq
        assert eq.source.currentData()==0 and eq.source.count()==1
        assert obs.order[0].stem in eq.source.toolTip()
        assert "2 Trace" not in eq.source.itemText(0)
        deadline=time.perf_counter()+2
        while eq.fs.currentData() is None and time.perf_counter()<deadline:
            time.sleep(.01);eq._refresh_fs(force=True);app.processEvents()
        assert eq.fs.currentData()==48000
        assert not eq.fs.isEnabled()
        eq.target.setCurrentText("House")
        before=hashlib.sha256(obs.order[0].read_bytes()).hexdigest()
        eq.compute()
        end=time.monotonic()+15
        while eq.result is None and time.monotonic()<end:
            app.processEvents();time.sleep(.02)
        assert eq.result and eq.result.status=="PREVIEW_READY"
        assert hub.native_eq.source and len(eq.result.peqs)>0
        assert hashlib.sha256(obs.order[0].read_bytes()).hexdigest()==before
        tick(obs,{0,1})
        hub.tick();app.processEvents()
        assert eq.result is None
        assert hub.native_eq.source is None
        assert eq.source.currentData() is None
        assert not hub.eq.export.isEnabled()
    finally:
        hub.close();app.processEvents()

def test_gui_verified_count_zero_two_six_and_expiry():
    app=QApplication.instance() or QApplication([])
    obs=setup()
    engine=App(False);engine.timer.stop()
    engine.observer=obs
    engine.current_pair=None
    engine.current_traces=None
    engine._selection_verified=False
    hub=ToolHub(engine);hub.timer.stop();hub.native_eq.timer.stop()
    try:
        hub.select("eq")
        for idxs in [set(),{0,1},{0,1,2,3,4,5}]:
            tick(obs,idxs)
            # Qt offscreen has no foreground Smaart: exercise source
            # presentation directly, while hub.tick correctly invalidates
            # live locks when physical Smaart is not foreground.
            hub.eq.refresh_sources();app.processEvents()
            label=hub.eq.source.itemText(0)
            assert f"{len(idxs)} Trace" in label,label
            assert "Đang chờ 2 Trace" not in label
            assert hub.eq.source.currentData() is None
            assert not hub.eq.export.isEnabled()
        obs.invalidate_single()
        hub.tick();app.processEvents()
        assert "Đang xác minh 0/3" in hub.eq.source.itemText(0)
        for _ in range(3):tick(obs,{0})
        hub.eq.refresh_sources();app.processEvents()
        assert hub.eq.source.currentData()==0
        # Screenshot failure/no foreground invalidates, not stale 6 count.
        obs.invalidate_single()
        hub.tick();app.processEvents()
        assert hub.eq.source.currentData() is None
        assert hub.native_eq.source is None
    finally:hub.close();app.processEvents()
