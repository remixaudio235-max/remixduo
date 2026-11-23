"""V8.160 strict source/native EQ export proof plus diagnostic trace gate."""
import os,time,hashlib
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from native_eq_mag_v06 import frame_is_fresh_for_window
import native_eq_mag_v06 as native
from signal_tools_gui_v813 import EQDialog


def gate(tmp_path,monkeypatch):
    f=tmp_path/"original.trf"
    f.write_bytes(b"native-source-original")
    stat=f.stat()
    token=(str(f),stat.st_mtime_ns,stat.st_size,3)
    frame=NS(hwnd=900,window_rect=(0,0,1920,1080),
             source_identity="identity-A",revision=6,
             identity_verified=True,created=time.monotonic())
    source=NS(source_name=f.stem,source_identity="identity-A",revision=6)
    g=NS(source=source,frame=frame,approved_token=token,
         future=None,last_native_drop="",_source_binding_ok=lambda:True)
    fstate=NS(hz=48000)
    eq=NS(_native_guard=g,_export_source_token=token,
          _export_snapshot=object(),result=object(),
          _verified_single=lambda:token,
          _fs_snapshot=fstate,_saved_fs=lambda:fstate,
          _export_file_sha=hashlib.sha256(f.read_bytes()).hexdigest())
    monkeypatch.setattr(native.win32gui,"IsWindow",lambda h:h==900)
    monkeypatch.setattr(native.win32gui,"IsIconic",lambda h:False)
    monkeypatch.setattr(native.win32gui,"GetWindowRect",
                        lambda h:(0,0,1920,1080))
    return eq,g,f,token


def test_fresh_independently_verified_native_proof_enables_export(tmp_path,monkeypatch):
    eq,g,f,token=gate(tmp_path,monkeypatch)
    assert EQDialog._native_export_ok(eq,check_sha=True)
    assert EQDialog._export_hold_reason_v8160(eq)=="native_verified_and_file_current"


@pytest.mark.parametrize("blocked",[
    "tick_unverified","token_mismatch","missing_frame","wrong_identity",
    "expired_frame","wrong_viewport","changed_fs","bad_sha"])
def test_source_or_pixel_proof_must_fail_closed(tmp_path,monkeypatch,blocked):
    eq,g,f,token=gate(tmp_path,monkeypatch)
    if blocked=="tick_unverified":
        eq._verified_single=lambda:None
    elif blocked=="token_mismatch":
        g.approved_token=(token[0],token[1],token[2],token[3]+1)
    elif blocked=="missing_frame":
        g.frame=None
    elif blocked=="wrong_identity":
        g.frame.source_identity="identity-B"
    elif blocked=="expired_frame":
        g.frame.created=time.monotonic()-1.
    elif blocked=="wrong_viewport":
        g.frame.window_rect=(0,0,1919,1080)
    elif blocked=="changed_fs":
        eq._saved_fs=lambda:NS(hz=44100)
    elif blocked=="bad_sha":
        stat=f.stat()
        f.write_bytes(b"source-hash-is-changed")
        assert f.stat().st_size==stat.st_size
        os.utime(f,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    assert not EQDialog._native_export_ok(eq,check_sha=True),blocked
    assert EQDialog._export_hold_reason_v8160(eq)!="native_verified_and_file_current" or blocked=="bad_sha"


def test_old_frame_never_approved_just_because_tick_valid(tmp_path,monkeypatch):
    eq,g,f,token=gate(tmp_path,monkeypatch)
    g.frame.created=time.monotonic()-2
    assert eq._verified_single()==token
    assert not frame_is_fresh_for_window(g.frame,900)
    assert not EQDialog._native_export_ok(eq)
    assert EQDialog._export_hold_reason_v8160(eq)=="native_frame_expired_or_viewport_changed"
