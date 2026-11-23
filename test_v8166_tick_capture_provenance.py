"""V8.166 tick provenance: no cache-derived rearm, no cross-host or frame replay.

Pure/offscreen tests. No generator, audio routing, disk mutation of Smaart data.
"""
from pathlib import Path
import time
from live_sync_v7 import LiveDataBarV7, SyncResult
from stable_ticks_v824 import StableTickGate
from test_v8121_smaart8_ticks import _observer,FIX,HOST
from PIL import Image

NAMES=("c:/smaart/trf/a.trf","c:/smaart/trf/b.trf")
SRC=(17,"c:/smaart/trf")


def result(frame,*,source=SRC,active=NAMES,witness=None,status=None):
    active=tuple(active)
    return SyncResult(
        tuple(active) if len(active)==2 else None,
        status or "Verified viewport 8 rows; cached 8/8 rows",
        8,8,True,float(frame),active,0,
        source,frame,active if witness is None else tuple(witness))


def test_three_distinct_native_frames_commit_pair():
    gate=StableTickGate(required=3)
    states=[gate.evaluate(result(i),NAMES,0) for i in (1,2,3)]
    assert [d.state for d in states]==["pending","pending","valid"]
    assert gate.committed==NAMES
    assert gate.history[-1]["frame_id"]==3


def test_replayed_native_frame_revokes_current_authorization():
    gate=StableTickGate()
    for i in (1,2,3):gate.evaluate(result(i),NAMES,0)
    assert gate.committed==NAMES
    rejected=gate.evaluate(result(3),NAMES,0)
    assert rejected.state=="transient"
    assert rejected.reason=="REPLAYED_OR_OUT_OF_ORDER_NATIVE_FRAME"
    assert gate.stable==0
    assert gate.evaluate(result(4),NAMES,0).state=="pending"
    assert gate.evaluate(result(5),NAMES,0).state=="pending"
    assert gate.evaluate(result(6),NAMES,0).state=="valid"


def test_new_host_even_same_paths_requires_new_three_frames():
    gate=StableTickGate()
    for i in (1,2,3):gate.evaluate(result(i),NAMES,0)
    assert gate.committed==NAMES
    new=(42,SRC[1])
    one=gate.evaluate(result(1,source=new),NAMES,0)
    assert one.state=="pending" and gate.committed is None
    assert gate.evaluate(result(2,source=new),NAMES,0).state=="pending"
    assert gate.evaluate(result(3,source=new),NAMES,0).state=="valid"


def test_changed_trace_folder_same_hwnd_requires_rearm():
    gate=StableTickGate()
    for i in (1,2,3):gate.evaluate(result(i),NAMES,0)
    other=(SRC[0],"c:/smaart_v8/trf")
    assert gate.evaluate(result(1,source=other),NAMES,0).state=="pending"
    assert gate.committed is None


def test_cached_pair_without_native_witness_never_commits():
    gate=StableTickGate()
    for i in (1,2,3,4):
        out=gate.evaluate(result(i,witness=(NAMES[0],)),NAMES,0)
        assert out.state=="transient" and out.reason=="CHECKED_TRACE_NOT_VISIBLE_IN_FRAME"
    assert gate.committed is None and gate.stable==0
    for i in (5,6,7):
        decision=gate.evaluate(result(i),NAMES,0)
    assert decision.state=="valid"


def test_explicit_one_or_three_checked_never_grants_2trace():
    gate=StableTickGate()
    for n in (NAMES[:1],NAMES+("c:/smaart/trf/c.trf",)):
        gate=StableTickGate()
        for i in (1,2,3):
            d=gate.evaluate(result(i,active=n),n,0)
        assert d.state=="invalid" and gate.committed is None


def make_observer(tmp_path):
    items=[]
    for name in ("a.trf","b.trf","c.trf"):
        f=tmp_path/name
        f.write_bytes(b"abc")
        items.append(f)
    o=LiveDataBarV7(tmp_path)
    o.hwnd=17
    o.order=items
    o.ready=True
    o.states={0:"on",1:"off",2:"off"}
    o.row_seen_at={i:time.perf_counter() for i in range(3)}
    return o


def test_single_tick_cannot_rearm_from_other_visible_page(tmp_path):
    obs=make_observer(tmp_path)
    for k in range(3):obs.observe_single(time.perf_counter(),observed={0:"on",1:"off"})
    token=obs.current_single()
    assert token is not None
    obs.observe_single(time.perf_counter(),observed={1:"off",2:"off"})
    assert obs.current_single() is None
    assert obs.single_candidate==token[:3]
    for k in range(2):
        obs.observe_single(time.perf_counter(),observed={1:"off",2:"off"})
    assert obs.current_single() is None
    for k in range(3):
        obs.observe_single(time.perf_counter(),observed={0:"on",1:"off"})
    assert obs.current_single()==token


def test_two_tick_pair_requires_both_icons_in_the_current_page(tmp_path):
    o=make_observer(tmp_path)
    o.states={0:"on",1:"on",2:"off"}
    now=time.perf_counter()
    o.row_seen_at={i:now for i in range(3)}
    assert o._pair(observed={0:"on",1:"on"})==tuple(map(str,o.order[:2]))
    assert o._pair(observed={0:"on",2:"off"}) is None
    assert o._pair(observed={1:"on",2:"off"}) is None


def test_clear_removes_stale_colors_and_source_locks(tmp_path):
    o=make_observer(tmp_path)
    o.colors_by_name[str(o.order[0])]="#FF0000"
    for i in range(3):o.observe_single(time.perf_counter(),observed={0:"on"})
    assert o.current_single() is not None
    o.clear("host/edition changed")
    assert not o.colors_by_name and not o.ready
    assert o.current_single() is None


def test_smaart8_pixel_reader_emits_native_provenance(monkeypatch,tmp_path):
    o=_observer(monkeypatch,tmp_path,Image.open(FIX))
    first=o.poll(77)
    second=o.poll(77)
    assert first.source_id==(77,str(o.folder))
    assert second.frame_id==first.frame_id+1
    assert first.observed_active_names==first.active_names
    assert second.observed_active_names==second.active_names


def test_smaart8_change_window_clears_cached_colors_and_rearms(monkeypatch,tmp_path):
    o=_observer(monkeypatch,tmp_path,Image.open(FIX))
    o.poll(77)
    o.colors_by_name["old.trf"]="#ABCDEF"
    other=o.poll(99)
    assert other.source_id==(99,str(o.folder))
    assert "old.trf" not in o.colors_by_name
    assert o.hwnd==99



def test_minimized_suite_never_attempts_native_scan(monkeypatch,tmp_path):
    import live_sync_v7 as live
    o=make_observer(tmp_path)
    for _ in range(3):o.observe_single(time.perf_counter(),observed={0:"on"})
    assert o.current_single() is not None
    monkeypatch.setattr(live.win32gui,"IsIconic",lambda hwnd:True)
    def must_not_capture(*a,**k):
        raise AssertionError("PrintWindow must not run while minimized")
    monkeypatch.setattr(live,"printwindow_image",must_not_capture)
    r=o.poll(17)
    assert r.pair is None
    assert r.status=="Smaart viewport unavailable: minimized"
    assert r.source_id==(17,str(tmp_path))
    assert r.frame_id is None
    assert o.current_single() is None
    assert o.single_candidate is not None


def test_minimized_smaart8_never_reads_v8_icons(monkeypatch,tmp_path):
    import live_sync_v7 as live
    import smaart8_databar_v8121 as v8
    o=_observer(monkeypatch,tmp_path,Image.open(FIX))
    monkeypatch.setattr(live.win32gui,"IsIconic",lambda hwnd:True)
    def forbidden(*a,**kwargs):
        raise AssertionError("Cannot scan minimized v8 Data Bar")
    monkeypatch.setattr(v8,"v8_row_states",forbidden)
    r=o.poll(77)
    assert r.pair is None and "minimized" in r.status
    assert r.frame_id is None
    assert r.source_id==(77,str(o.folder))
