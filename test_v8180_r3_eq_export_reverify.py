"""V8.180 R3 AutoEQ export: late native proof recovery without unsafe shortcuts."""
import os,time,hashlib
from types import SimpleNamespace as NS
from pathlib import Path
import pytest
from signal_tools_gui_v813 import EQDialog
import native_eq_mag_v06 as mag

class Timer:
    def __init__(self):
        self.running=False
        self.starts=0
    def start(self):
        self.running=True
        self.starts+=1
    def stop(self):
        self.running=False

class Dummy:
    _native_export_ok=EQDialog._native_export_ok
    _export_hold_reason_v8160=EQDialog._export_hold_reason_v8160
    _recheck_preconditions=EQDialog._recheck_preconditions
    _export_retry_tick_state=EQDialog._export_retry_tick_state
    _stop_export_recheck=EQDialog._stop_export_recheck
    _poll_export_recheck=EQDialog._poll_export_recheck
    _open_verified_export_eq=None
    _refresh_export_gate=lambda self:None
    _last_notice=[]
    def warning(self,msg):
        self.warnings.append(str(msg))
    def notice(self,msg,graph=None):
        self.notices.append(str(msg))

@pytest.fixture
def context(tmp_path,monkeypatch):
    f=tmp_path/"original.trf";f.write_bytes(b"immutable native original")
    stat=f.stat();sha=hashlib.sha256(f.read_bytes()).hexdigest()
    token=(str(f),stat.st_mtime_ns,stat.st_size,10)
    source=NS(source_name=f.stem,source_identity="id1",revision=5)
    frame=NS(hwnd=900,window_rect=(0,0,1920,1040),
             source_identity="id1",revision=5,identity_verified=True,
             created=time.monotonic()-2.)
    tick_calls=[]
    guard=NS(source=source,frame=frame,approved_token=token,
             future=None,last_native_drop="",_source_binding_ok=lambda:True,
             tick=lambda:tick_calls.append("tick"))
    fs=NS(hz=48000)
    d=Dummy()
    d._serial=12
    d._export_source_token=token
    d._native_guard=guard
    d._export_snapshot=object()
    d.result=NS(status="PREVIEW_READY")
    d._fs_snapshot=fs
    d._saved_fs=lambda:fs
    d._export_file_sha=sha
    d._verified_single=lambda:token
    d._export_recheck_timer=Timer()
    d._export_recheck_context=None
    d.engine=NS(graph_mag=None)
    d.warnings=[];d.notices=[];d.opened=[]
    def commit_after_final_hash():
        if EQDialog._native_export_ok(d,check_sha=True):
            d.opened.append("opened")
        else:
            d.warnings.append("Export HOLD: final source SHA or native proof failed")
    d._open_verified_export_eq=commit_after_final_hash
    monkeypatch.setattr(mag.win32gui,"IsWindow",lambda _:True)
    monkeypatch.setattr(mag.win32gui,"IsIconic",lambda _:False)
    monkeypatch.setattr(mag.win32gui,"GetWindowRect",lambda _:(0,0,1920,1040))
    return d,guard,frame,f,token,tick_calls

def test_stale_native_frame_waits_until_independently_fresh(context):
    d,g,frame,f,token,ticks=context
    assert not d._native_export_ok(check_sha=True)
    assert d._export_hold_reason_v8160()=="native_frame_expired_or_viewport_changed"
    EQDialog.export_eq(d)
    assert d._export_recheck_timer.running
    assert d.opened==[] and ticks
    frame.created=time.monotonic()
    EQDialog._poll_export_recheck(d)
    assert d.opened==["opened"]
    assert not d._export_recheck_timer.running
    assert d.warnings==[]

def test_current_native_frame_opens_without_retry(context):
    d,g,frame,*_=context
    frame.created=time.monotonic()
    EQDialog.export_eq(d)
    assert d.opened==["opened"]
    assert not d._export_recheck_timer.running

def test_tick_change_during_retry_fails_closed(context):
    d,g,frame,f,token,ticks=context
    EQDialog.export_eq(d)
    d._verified_single=lambda:None
    frame.created=time.monotonic()
    EQDialog._poll_export_recheck(d)
    assert d.opened==[]
    assert not d._export_recheck_timer.running
    assert d.warnings and "Trace" in d.warnings[-1]

def test_source_sha_change_during_retry_fails_closed(context):
    d,g,frame,f,token,ticks=context
    EQDialog.export_eq(d)
    st=f.stat()
    f.write_bytes(b"M"*st.st_size)
    os.utime(f,ns=(st.st_atime_ns,st.st_mtime_ns))
    frame.created=time.monotonic()
    EQDialog._poll_export_recheck(d)
    assert d.opened==[] and d.warnings
    assert not d._export_recheck_timer.running

def test_viewport_moved_rejects_immediately(context):
    d,g,frame,f,token,ticks=context
    frame.window_rect=(0,0,1800,1040)
    EQDialog.export_eq(d)
    assert d.opened==[] and not d._export_recheck_timer.running
    assert d.warnings

def test_wrong_native_identity_never_starts_retry(context):
    d,g,frame,f,token,ticks=context
    g.source.source_identity="other"
    EQDialog.export_eq(d)
    assert not d._export_recheck_timer.running and not d.opened
    assert d.warnings

def test_pending_retry_timeout_fails_closed(context):
    d,g,frame,f,token,ticks=context
    EQDialog.export_eq(d)
    assert d._export_recheck_context
    tk,srl,sha,t=d._export_recheck_context
    d._export_recheck_context=(tk,srl,sha,time.monotonic()-5.)
    EQDialog._poll_export_recheck(d)
    assert d.opened==[]
    assert not d._export_recheck_timer.running
    assert any("HOLD" in m for m in d.warnings)

def test_recalculation_generation_change_blocks_stale_retry(context):
    d,g,frame,f,token,ticks=context
    EQDialog.export_eq(d)
    d._serial+=1
    frame.created=time.monotonic()
    EQDialog._poll_export_recheck(d)
    assert d.opened==[] and d.warnings


def _put_rearming_context(d,g,token):
    obs=NS(ready=True,order=["one","two"],states={0:"on",1:"unknown"},
           single_candidate=tuple(token[:3]),current_single=lambda:None)
    d.engine.observer=obs
    d._verified_single=lambda:obs.current_single()
    g._source_binding_ok=lambda:d._verified_single()==token
    return obs

def test_midscan_tick_rearm_waits_until_3of3_then_export(context):
    d,g,frame,f,token,ticks=context
    obs=_put_rearming_context(d,g,token)
    EQDialog.export_eq(d)
    assert d._export_recheck_timer.running and d.opened==[]
    EQDialog._poll_export_recheck(d)
    assert d.opened==[] and not d.warnings
    # Observer independently accepts 3/3 after a transient scan.
    obs.states={0:"on",1:"off"}
    obs.current_single=lambda:token
    frame.created=time.monotonic()
    EQDialog._poll_export_recheck(d)
    assert d.opened==["opened"]
    assert not d._export_recheck_timer.running

def test_explicit_two_ticks_abort_without_export(context):
    d,g,frame,f,token,ticks=context
    obs=_put_rearming_context(d,g,token)
    EQDialog.export_eq(d)
    obs.states={0:"on",1:"on"}
    EQDialog._poll_export_recheck(d)
    assert d.opened==[] and d.warnings
    assert not d._export_recheck_timer.running

def test_explicit_zero_ticks_abort_without_export(context):
    d,g,frame,f,token,ticks=context
    obs=_put_rearming_context(d,g,token)
    EQDialog.export_eq(d)
    obs.states={0:"off",1:"off"}
    EQDialog._poll_export_recheck(d)
    assert d.opened==[] and d.warnings

def test_rearming_candidate_path_changed_must_abort(context):
    d,g,frame,f,token,ticks=context
    obs=_put_rearming_context(d,g,token)
    EQDialog.export_eq(d)
    obs.single_candidate=("other.trf",1,20)
    EQDialog._poll_export_recheck(d)
    assert d.opened==[] and d.warnings

def test_rearm_never_waits_beyond_1p5_seconds(context):
    d,g,frame,f,token,ticks=context
    _put_rearming_context(d,g,token)
    EQDialog.export_eq(d)
    tk,serial,sha,start=d._export_recheck_context
    d._export_recheck_context=(tk,serial,sha,time.monotonic()-1.6)
    EQDialog._poll_export_recheck(d)
    assert d.opened==[] and not d._export_recheck_timer.running
    assert any("3/3" in w for w in d.warnings)

def test_metadata_changed_during_wait_fails_closed(context):
    d,g,frame,f,token,ticks=context
    obs=_put_rearming_context(d,g,token)
    EQDialog.export_eq(d)
    f.write_bytes(b"fresh data changes original length and metadata")
    EQDialog._poll_export_recheck(d)
    assert d.opened==[] and d.warnings

def test_poll_never_hashes_large_trf_again(context,monkeypatch):
    d,g,frame,f,token,ticks=context
    original=hashlib.sha256
    count=[]
    def spy(data=b""):
        count.append(len(data))
        return original(data)
    monkeypatch.setattr(hashlib,"sha256",spy)
    EQDialog.export_eq(d)
    assert len(count)==1, "Initial click SHA must check source exactly once"
    for _ in range(12):
        EQDialog._poll_export_recheck(d)
    assert len(count)==1, "90-ms polls must never rehash TRF"
    frame.created=time.monotonic()
    EQDialog._poll_export_recheck(d)
    assert d.opened==["opened"]

def test_verified_single_different_generation_is_not_silently_rebound(context):
    d,g,frame,f,token,ticks=context
    obs=_put_rearming_context(d,g,token)
    EQDialog.export_eq(d)
    obs.current_single=lambda:(token[0],token[1],token[2],token[3]+1)
    EQDialog._poll_export_recheck(d)
    assert d.opened==[] and d.warnings

def test_rearm_candidate_still_requires_identity_verified(context):
    d,g,frame,f,token,ticks=context
    _put_rearming_context(d,g,token)
    frame.identity_verified=False
    EQDialog.export_eq(d)
    assert d.warnings and not d._export_recheck_timer.running

def test_rearm_candidate_still_requires_saved_fs(context):
    d,g,frame,f,token,ticks=context
    _put_rearming_context(d,g,token)
    d._saved_fs=lambda:NS(hz=44100)
    EQDialog.export_eq(d)
    assert d.warnings and not d._export_recheck_timer.running
