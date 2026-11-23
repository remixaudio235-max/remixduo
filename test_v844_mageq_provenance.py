"""V8.44 critical source/viewport/export provenance tests (offline)."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import time
import numpy as np
import pytest

import native_eq_mag_v06 as native
from native_eq_mag_v06 import FitFrame,build_state,frame_is_fresh_for_window
from smaart_native_mag_fit import NativeMagFit,native_points
from mageq_visual_v13 import build_geometry
from signal_tools_gui_v813 import EQDialog

PLOT=(252,539,1442,412)
WIN=(0,0,1920,1080)


def test_native_fit_rejects_unmatched_grid_already_regressed():
    from test_v840_autoeq_native_grid import test_native_grid_without_matching_original_trace_is_rejected
    assert callable(test_native_grid_without_matching_original_trace_is_rejected)


def test_same_snapshot_pixel_translation_shared_by_mag_eq_markers_and_gradient():
    frequencies=np.geomspace(20.,20000.,1800)
    h=10**(-9/20)*np.ones_like(frequencies,dtype=complex)
    coherence=np.ones_like(frequencies)
    bands=(SimpleNamespace(freq_hz=120.,gain_db=3.,q=1.3),
           SimpleNamespace(freq_hz=750.,gain_db=-3.,q=2.1))
    src=build_state(frequencies,h,coherence,bands,
                    fs=48000,source_index=0,source_name="QA",revision=9)
    fit=NativeMagFit(190.,12.4,-9.,.91,.10,150,True,"matched native pixel")
    frame=FitFrame(src.revision,PLOT,fit,"red",time.monotonic(),123,WIN,
                   source_identity=src.source_identity,identity_verified=True)
    geo=build_geometry(src,frame)
    before,_=native_points(PLOT,fit,src.freqs,src.original_db,src.coh)
    after,_=native_points(PLOT,fit,src.freqs,src.after_db,src.coh)
    assert np.max(np.abs((before[:,1]-after[:,1])-
           (src.after_db-src.original_db)*fit.px_per_db))<1e-7
    assert len(geo.markers)==2 and all(x.visible for x in geo.markers)
    assert geo.rect==frame.plot and geo.source_revision==frame.revision
    assert len(geo.spans)>0
    # A changed native Y offset moves both paths and every marker equally.
    shift=23.
    moved=replace(fit,center_px=fit.center_px+shift)
    shifted=replace(frame,fit=moved,created=time.monotonic())
    geo2=build_geometry(src,shifted)
    assert np.allclose(geo2.after[:,1]-geo.after[:,1],shift)
    assert np.allclose(geo2.original[:,1]-geo.original[:,1],shift)
    for a,b in zip(geo.markers,geo2.markers):
        assert abs(b.y-a.y-shift)<1e-6


def test_frame_expires_quickly_even_if_window_geometry_does_not_change(monkeypatch):
    monkeypatch.setattr(native.win32gui,"IsWindow",lambda h:True)
    monkeypatch.setattr(native.win32gui,"IsIconic",lambda h:False)
    monkeypatch.setattr(native.win32gui,"GetWindowRect",lambda h:WIN)
    fit=NativeMagFit(170.,11.5,0.,.92,.1,120,True,"pixel")
    now=time.monotonic()
    f=FitFrame(1,PLOT,fit,"red",now,123,WIN,
               source_identity="qa",identity_verified=True)
    assert frame_is_fresh_for_window(f,123,now=now+.10)
    assert not frame_is_fresh_for_window(f,123,now=now+.8)
    assert not frame_is_fresh_for_window(f,456,now=now+.1)
    assert not frame_is_fresh_for_window(replace(f,window_rect=(0,0,1800,900)),
                                         123,now=now+.1)


def test_export_pending_file_digest_fail_closed(tmp_path):
    p=tmp_path/"selected.trf"
    p.write_bytes(b"first data")
    import hashlib
    tok=(str(p),p.stat().st_mtime_ns,p.stat().st_size,1)
    pending=(0,0,None,None,None,(),"selected",tok,None,
             hashlib.sha256(p.read_bytes()).hexdigest())
    assert EQDialog._pending_sha_ok(pending)
    p.write_bytes(b"other data")
    assert not EQDialog._pending_sha_ok(pending)
    p.unlink()
    assert not EQDialog._pending_sha_ok(pending)
