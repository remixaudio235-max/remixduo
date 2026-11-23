from dataclasses import replace
import time
import pytest

def window():
    from remix_duo.platforms.contracts import WindowRef,WindowState
    return WindowState(WindowRef('darwin',51,'start-1','99'),(10.,20.,800.,600.),'Smaart',True,True,'9.6.0')

def test_native_snapshot_fails_on_geometry_process_and_age_change():
    from remix_duo.platforms.contracts import CapturedFrame
    w=window();frame=CapturedFrame(w,b'png',800,600,100.)
    assert frame.valid_for(w,100.1)
    assert not frame.valid_for(w,101.)
    assert not frame.valid_for(replace(w,rect=(11,20,800,600)),100.1)
    assert not frame.valid_for(replace(w,foreground=False),100.1)
    assert not frame.valid_for(replace(w,ref=replace(w.ref,process_started='new')),100.1)

def test_mac_discovery_requires_bundle_version_process_start_and_real_window():
    from remix_duo.platforms.macos.discovery import select_windows
    app=dict(pid=51,started='123',bundle='com.rationalacoustics.smaart',version='9.6.0')
    raw=dict(pid=51,id=99,layer=0,onscreen=True,title='Smaart',rect=(10,20,800,600))
    assert select_windows([app],[raw],51)[0].ref==window().ref.__class__('darwin',51,'123','99')
    for bad in [dict(app,bundle='com.fake.smaart'),dict(app,started=''),dict(app,version='1.0')]:
        assert not select_windows([bad],[raw],51)
    assert not select_windows([app],[dict(raw,layer=3)],51)
    assert not select_windows([app],[dict(raw,rect=(0,0,30,30))],51)

def test_ax_row_evidence_rejects_offscreen_unknown_duplicate_and_partial_rows():
    from remix_duo.platforms.macos.selection import TraceRow,selection_from_rows
    w=window()
    rows=[TraceRow('a.trf',True,True),TraceRow('b.trf',True,True),TraceRow('c.trf',False,True)]
    e=selection_from_rows(w.ref,rows,total=3,observed_at=100)
    assert e.verified_pair(w.ref,100.1)==('a.trf','b.trf')
    for invalid in [rows[:2],rows+[TraceRow('a.trf',False,True)],
                    rows[:2]+[TraceRow('c.trf',False,False)],
                    rows[:2]+[TraceRow('c.trf',None,True)]]:
        assert not selection_from_rows(w.ref,invalid,total=3,observed_at=100).complete

def test_ax_does_not_mistake_selected_highlight_for_enabled_trace():
    from remix_duo.platforms.macos.selection import checkbox_state
    assert checkbox_state({'AXSelected':True}) is None
    assert checkbox_state({'AXRole':'AXCheckBox','AXValue':1}) is True
    assert checkbox_state({'AXRole':'AXCheckBox','AXValue':0}) is False
    assert checkbox_state({'AXRole':'AXCheckBox','AXValue':2}) is None
    assert checkbox_state({'AXRole':'AXRow','AXValue':1}) is None

def test_late_capture_completion_never_updates_next_request():
    from remix_duo.platforms.macos.capture import CaptureResult
    a=CaptureResult();b=CaptureResult()
    a.cancel();a.finish(b'old',None)
    b.finish(b'new',None)
    assert a.value is None and b.value==b'new'

def test_missing_mac_framework_is_reported_as_capability_not_success(monkeypatch):
    from remix_duo.platforms.macos.services import MacServices
    from remix_duo.platforms.macos import permissions
    monkeypatch.setattr(permissions,'status',lambda:dict(accessibility=False,screen_capture=False,frameworks=False))
    cap=MacServices().native_capability()
    assert not cap.ready and 'HOLD' in cap.reason

def test_capture_configuration_has_no_audio_shadow_cursor_or_letterboxing():
    from remix_duo.platforms.macos.capture import configure_capture
    class Config:
        def __getattr__(self,name):
            return lambda value:setattr(self,name.removeprefix('set').removesuffix('_'),value)
    config=Config();configure_capture(config,window())
    assert config.CapturesAudio is False
    assert config.ShowsCursor is False
    assert config.IgnoreShadowsSingleWindow is True
    assert config.PreservesAspectRatio is False
    assert (config.Width,config.Height)==(800,600)
