"""V8.156: background/failed PrintWindow must not change immutable source generation.

Read-only observer + ToolHub orchestration; no Smaart, audio or mouse needed.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import time
import pytest
import live_sync_v7 as live
import signal_tools_gui_v813 as gui
from mageq_presentation_gate_v853 import keep_preview_on_partial_scan


def test_complete_tick_change_never_keeps_old_eq():
    token=("c:/original.trf",10,25,3)
    assert keep_preview_on_partial_scan(None,token,token[:3],None)
    assert not keep_preview_on_partial_scan(None,token,token[:3],0)
    assert not keep_preview_on_partial_scan(None,token,token[:3],2)


def observer(tmp_path):
    files=[]
    for i in range(2):
        path=tmp_path / f"trace{i}.trf"
        path.write_bytes(bytes([65+i])*20)
        files.append(path)
    o=live.LiveDataBarV7(tmp_path)
    o.hwnd=1234
    o.order=files
    o.ready=True
    o.states={0:"on",1:"off"}
    for _ in range(3):
        o.observe_single(time.perf_counter())
    assert o.current_single() is not None
    return o


def test_one_trace_survives_transient_but_new_work_is_blocked(tmp_path):
    o=observer(tmp_path)
    token=o.current_single()
    gen=o.single_generation
    o.suspend_single_transient()
    assert o.current_single() is None
    assert o.single_candidate==token[:3]
    assert o.single_generation==gen
    for _ in range(3):
        o.observe_single(time.perf_counter())
    assert o.current_single()==token


def test_verified_other_source_and_tick_count_hard_invalidate(tmp_path):
    o=observer(tmp_path)
    token=o.current_single()
    o.suspend_single_transient()
    o.states={0:"off",1:"on"}
    for _ in range(3):o.observe_single(time.perf_counter())
    assert o.current_single()!=token
    assert o.current_single()[0]!=token[0]
    o.states={0:"on",1:"on"}
    o.observe_single(time.perf_counter())
    assert o.current_single() is None
    assert o.single_candidate is None


def test_changed_file_bytes_reject_original_proof(tmp_path):
    o=observer(tmp_path)
    token=o.current_single()
    o.suspend_single_transient()
    Path(token[0]).write_bytes(b"changed-source-content")
    for _ in range(3):o.observe_single(time.perf_counter())
    assert o.current_single()!=token
    assert o.current_single()[1:3]!=token[1:3]


def run_hub_background(o,monkeypatch,*,window_alive=True,returned=None,pair_changed=False):
    monkeypatch.setattr(gui,"locate_smaart",lambda **kwargs:returned if returned is not None else NS(hwnd=9999,foreground=False))
    monkeypatch.setattr(gui.win32gui,"IsWindow",lambda hwnd:window_alive and hwnd==o.hwnd)
    calls=[]
    eq=NS(refresh_sources=lambda:calls.append("eq_refresh"),
          _refresh_export_gate=lambda:calls.append("eq_export_gate"))
    fir=NS(refresh_sources=lambda:calls.append("fir_refresh"),
           _refresh_export=lambda:calls.append("fir_export_gate"))
    engine=NS(observer=o,current_pair=None,current_traces=None,
              _target_is_foreground=lambda _hwnd:False,
              refresh_visibility=lambda:calls.append("visibility"),
              overlay_workspace_visible=True)
    hub=NS(engine=engine,eq=eq,fir=fir,native_eq=NS(hide=lambda:calls.append("native_hide")),
           _last_pair_key=("prior",) if pair_changed else ((),()),_was_target=False,
           hide=lambda:calls.append("hub_hide"),
           dock=NS(hide=lambda:calls.append("dock_hide")))
    gui.ToolHub.tick(hub)
    assert "native_hide" in calls and "eq_export_gate" in calls
    assert "fir_export_gate" in calls
    assert calls.count("fir_refresh")==1  # no duplicate on pair/overlay change
    assert engine.overlay_workspace_visible is False
    return calls


def test_hub_background_other_smaart_zorder_preserves_candidate(tmp_path,monkeypatch):
    o=observer(tmp_path)
    token=o.current_single()
    generation=o.single_generation
    for _ in range(5):
        run_hub_background(o,monkeypatch)
        assert o.current_single() is None
        assert o.single_candidate==token[:3]
        assert o.single_generation==generation
    for _ in range(3):o.observe_single(time.perf_counter())
    assert o.current_single()==token


def test_hub_pair_object_change_only_refreshes_fir_once(tmp_path,monkeypatch):
    o=observer(tmp_path)
    calls=run_hub_background(o,monkeypatch,pair_changed=True)
    assert calls.count("fir_refresh")==1


def test_hub_missing_bound_hwnd_invalidates(tmp_path,monkeypatch):
    o=observer(tmp_path)
    run_hub_background(o,monkeypatch,window_alive=False)
    assert o.current_single() is None
    assert o.single_candidate is None


def test_hub_explicit_other_foreground_host_invalidates(tmp_path,monkeypatch):
    o=observer(tmp_path)
    run_hub_background(o,monkeypatch,returned=NS(hwnd=5678,foreground=True))
    assert o.single_candidate is None


def _eq_worker_fixture(tmp_path,*,source_unchanged=True,sha_ok=True):
    from signal_tools_gui_v813 import EQDialog
    path=tmp_path/"one.trf"
    path.write_bytes(b"fixture")
    st=path.stat()
    token=(str(path),st.st_mtime_ns,st.st_size,3)
    snap=NS(hz=48000)
    current=(token if source_unchanged else (str(path),st.st_mtime_ns+1,st.st_size,4))
    messages=[]
    result=NS(status="NO_EQ_NEEDED",peqs=(),source="one",
              rms_before=0.0,rms_after=0.0,fs=48000,
              filter_limit=8,filters_auto=False,limits_auto=False,warnings=())
    fake=NS(
        _serial=7,
        _pending_native=(7,0,[100.],[1.+0j],[.9],(111,222),
                         "one",token,snap,"expected_sha"),
        engine=NS(current_traces=(object(),object(),object()),
                  observer=NS(current_single=lambda:current)),
        calculate=NS(setEnabled=lambda value:messages.append(("enabled",value))),
        source=NS(currentData=lambda:0),
        _verified_single=lambda:current,
        _saved_fs=lambda:snap,
        _pending_sha_ok=lambda pending:sha_ok,
        native_ready=NS(emit=lambda *args:messages.append(("paint_signal",args))),
        native_clear=NS(emit=lambda:messages.append(("clear_signal",))),
        summary=NS(setText=lambda msg:messages.append(("summary",msg))),
        details=NS(setPlainText=lambda msg:messages.append(("details",msg))),
        filter_count=NS(value=lambda:8),
        _refresh_export_gate=lambda:messages.append(("refresh_export",)),
    )
    return EQDialog,fake,result,messages


def test_eq_worker_accepts_same_trf_even_if_overlay_objects_recreated(tmp_path):
    klass,fake,result,messages=_eq_worker_fixture(tmp_path)
    # pending SUM object IDs (111,222) no longer exist in the GUI, but
    # EQ was calculated from a single immutable TRF token.
    klass._finish(fake,7,NS(result=lambda:result))
    assert fake.result is result
    assert any(item[0]=="paint_signal" for item in messages)
    assert not any(item[0]=="clear_signal" for item in messages)


def test_eq_worker_rejects_real_source_change_or_sha_mismatch(tmp_path):
    for changed,sha_ok in ((True,True),(False,False)):
        klass,fake,result,messages=_eq_worker_fixture(
            tmp_path,source_unchanged=not changed,sha_ok=sha_ok)
        klass._finish(fake,7,NS(result=lambda:result))
        assert getattr(fake,"result",None) is None
        assert any(item[0]=="clear_signal" for item in messages)
