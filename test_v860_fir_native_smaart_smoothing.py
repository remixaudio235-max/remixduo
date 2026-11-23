"""V8.60: FIR native registration must match Smaart's visible smoothing.

All mock tests are read-only, no Smaart or audio device is operated.
"""
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image

import fir_native_v846 as n
from smaart_eq_color_select import ColorFit
from smaart_native_mag_fit import NativeMagFit
from tf_display_smoothing import smooth_log_octaves
from test_v846_fir_native import source,frame,MAG,PHASE,WIN


def setup(monkeypatch,*,smoothing=1/6,mag_verified=True,phase_verified=True):
    src,_=source()
    snapshot=SimpleNamespace(mag_oct=smoothing,phase_oct=1/6,
        mag_verified=mag_verified,phase_verified=phase_verified)
    counts={"uia":0,"capture":0,"fit":0,"title":0,"phase":0}
    def role(hwnd):
        counts["uia"]+=1
        return SimpleNamespace(mag=MAG,phase=PHASE)
    def capture(hwnd):
        counts["capture"]+=1
        return Image.new("RGB",(WIN[2],WIN[3]),(7,12,19)),WIN
    def titles(image,rect,roles):
        counts["title"]+=1
        return (MAG,1.) if roles==(PHASE,MAG) else None
    fit=NativeMagFit(186.,11.,0.,1.,0.,224,True,"QA native original")
    def choose(image,rect,window,f,db,coh):
        counts["fit"]+=1
        np.testing.assert_allclose(db,smooth_log_octaves(
            src.freqs,src.original_db,smoothing),atol=1e-12)
        return ColorFit("blue",fit,0.,True)
    def single(image,rect,window,f,db,coh,*,trace_color):
        counts["fit"]+=1
        assert trace_color=="blue"
        np.testing.assert_allclose(db,smooth_log_octaves(
            src.freqs,src.original_db,smoothing),atol=1e-12)
        return fit
    def phasefit(*args):
        counts["phase"]+=1
        return 361.,.97
    monkeypatch.setattr(n,"read_saved_smooth",lambda:snapshot)
    monkeypatch.setattr(n,"locate_role_plots",role)
    monkeypatch.setattr(n,"capture_native_window",capture)
    monkeypatch.setattr(n,"detect_magnitude_rect",titles)
    monkeypatch.setattr(n,"choose_color_fit",choose)
    monkeypatch.setattr(n,"fit_native_mag",single)
    monkeypatch.setattr(n,"phase_native_fit",phasefit)
    monkeypatch.setattr(n,"fit_native_mag_grid",lambda *a:SimpleNamespace(
        accepted=False,confidence=0.,px_per_db=11.))
    monkeypatch.setattr(n,"rasterize_fir_frame",lambda s,f:f)
    monkeypatch.setattr(n.win32gui,"IsWindow",lambda h:True)
    monkeypatch.setattr(n.win32gui,"IsIconic",lambda h:False)
    monkeypatch.setattr(n.win32gui,"GetWindowRect",lambda h:WIN)
    return src,counts,snapshot


def test_full_frame_uses_smaart_1_6_source_display_not_raw(monkeypatch):
    src,calls,_=setup(monkeypatch)
    result=n.native_fir_frame(123,src,center_phase_top=360.)
    assert result is not None and result.mag_smooth_oct==1/6
    assert result.phase_verified and result.phase_score==.97
    assert result.mag_fit.score==1.
    assert calls=={"uia":1,"capture":1,"fit":1,"title":1,"phase":1}
    assert np.array_equal(src.original_db,src.original_db.copy())


def test_full_frame_accepts_verified_one_twelfth_mag_smoothing(monkeypatch):
    src,calls,_=setup(monkeypatch,smoothing=1/12)
    result=n.native_fir_frame(123,src,center_phase_top=360.)
    assert result is not None and result.mag_smooth_oct==1/12
    assert result.phase_verified and calls["fit"]==1


def test_fast_native_frame_rechecks_pixels_but_skips_expensive_uia(monkeypatch):
    src,calls,_=setup(monkeypatch)
    first=n.native_fir_frame(123,src)
    second=n.native_fir_frame(123,src,prior=first)
    assert second is not None and second.created>=first.created
    assert calls["uia"]==1
    assert calls["capture"]==2
    assert calls["fit"]==2
    assert calls["title"]==2 and calls["phase"]==2


def test_verified_role_hint_rechecks_fresh_pixels_without_uia(monkeypatch):
    src,calls,_=setup(monkeypatch,smoothing=1/12)
    result=n.native_fir_frame(123,src,center_phase_top=360.,
                              role_hint=(PHASE,MAG))
    assert result is not None and result.phase_verified
    assert calls["uia"]==0
    assert calls["capture"]==1 and calls["title"]==1
    assert calls["fit"]==1 and calls["phase"]==1


def test_unverified_smoothing_fails_closed(monkeypatch):
    src,calls,_=setup(monkeypatch,mag_verified=False)
    assert n.native_fir_frame(123,src) is None
    assert calls["fit"]==0


def test_other_phase_smoothing_keeps_mag_but_holds_phase(monkeypatch):
    src,calls,snapshot=setup(monkeypatch)
    snapshot.phase_oct=1/12
    result=n.native_fir_frame(123,src)
    assert result is not None
    assert result.mag_fit.accepted
    assert not result.phase_verified
    assert calls["phase"]==0


def test_modified_window_bypasses_cached_geometry(monkeypatch):
    src,calls,_=setup(monkeypatch)
    first=n.native_fir_frame(123,src)
    monkeypatch.setattr(n.win32gui,"GetWindowRect",
                        lambda h:(20,0,1940,1080))
    result=n.native_fir_frame(123,src,prior=first)
    assert result is not None
    assert calls["uia"]==2


def test_invalid_fast_color_cannot_prove_wrong_source(monkeypatch):
    src,calls,_=setup(monkeypatch)
    first=n.native_fir_frame(123,src)
    bad=replace(first,source_identity="another-trace")
    result=n.native_fir_frame(123,src,prior=bad)
    assert result is not None and calls["uia"]==2
    monkeypatch.setattr(n,"fit_native_mag",lambda *a,**k:replace(
        first.mag_fit,accepted=False))
    monkeypatch.setattr(n,"choose_color_fit",lambda *a,**k:None)
    assert n.native_fir_frame(123,src,prior=first) is None


def test_mageq_predicted_raster_uses_same_smaart_smoothing(monkeypatch):
    src,_=source()
    f=replace(frame(src),mag_smooth_oct=1/6)
    points,valid=n.fir_mag_points(src,f)
    expected=smooth_log_octaves(src.freqs,src.after_db,1/6)
    np.testing.assert_allclose(points[:,1],f.mag_fit.y(expected),atol=1e-8)
    assert valid.sum()>100
    raw=n.fir_mag_points(src,replace(f,mag_smooth_oct=0.))[0]
    # Non-flat FIR response changes shape after display smoothing.
    assert np.max(abs(points[:,1]-raw[:,1]))>1e-5
