"""V8.53: role cached only when verified again on SAME fresh native pixels."""
from types import SimpleNamespace as NS
from dataclasses import replace
import time
import pytest
from PIL import Image
import native_eq_mag_v06 as n
from native_eq_mag_v06 import FitFrame,native_fit_worker
from smaart_native_mag_fit import NativeMagFit
from test_v847_autoeq_bypass_grid import model

MAG=(252,539,1442,412)
PHASE=(252,84,1442,412)
WIN=(0,0,1920,1040)


def test_cached_magnitude_layout_uses_one_fresh_capture_not_uia(monkeypatch):
    _,_,source=model()
    fit=NativeMagFit(205,11.5,1.,.99,.2,200,True,"verified source pixels")
    prior=FitFrame(source.revision,MAG,fit,"blue",time.monotonic()-.2,
        77,WIN,source.source_identity,True,True,PHASE)
    snap=Image.new("RGB",(1920,1040),"black")
    calls=dict(capture=0,detect=0,fit=0)
    monkeypatch.setattr(n.win32gui,"IsWindow",lambda hwnd:True)
    monkeypatch.setattr(n.win32gui,"IsIconic",lambda hwnd:False)
    monkeypatch.setattr(n.win32gui,"GetWindowRect",lambda hwnd:WIN)
    def capture(hwnd):
        calls["capture"]+=1
        return snap,WIN
    def role(*a):
        raise AssertionError("UIA role scan must not run when title verified")
    def detect(img,window,positions):
        calls["detect"]+=1
        assert img is snap and window==WIN
        assert positions==(PHASE,MAG)
        return MAG,1.
    def quick(img,mag,window,src,grid,old):
        calls["fit"]+=1
        assert img is snap and src.source_identity==source.source_identity
        assert old is prior and mag==MAG and window==WIN
        return replace(prior,created=time.monotonic(),phase_plot=PHASE)
    monkeypatch.setattr(n,"capture_native_window",capture)
    monkeypatch.setattr(n,"locate_role_plots",role)
    monkeypatch.setattr(n,"detect_magnitude_rect",detect)
    monkeypatch.setattr(n,"fit_native_mag_grid",lambda *a,**kw:object())
    monkeypatch.setattr(n,"saved_mag_grid_interval",lambda:3.)
    monkeypatch.setattr(n,"_fast_refit_same_source",quick)
    result=native_fit_worker(77,source,"blue",prior)
    assert result is not None and result.phase_plot==PHASE
    assert result.created>prior.created
    assert calls==dict(capture=1,detect=1,fit=1)


def test_stale_title_never_reuses_cache_on_changed_plot(monkeypatch):
    _,_,source=model()
    fit=NativeMagFit(205,11.5,1.,.99,.2,200,True,"verified")
    prior=FitFrame(source.revision,MAG,fit,"blue",time.monotonic(),
        77,WIN,source.source_identity,True,True,PHASE)
    calls=[]
    monkeypatch.setattr(n.win32gui,"IsWindow",lambda hwnd:True)
    monkeypatch.setattr(n.win32gui,"IsIconic",lambda hwnd:False)
    monkeypatch.setattr(n.win32gui,"GetWindowRect",lambda hwnd:WIN)
    monkeypatch.setattr(n,"capture_native_window",
                        lambda hwnd:(Image.new("RGB",(1920,1040),"black"),WIN))
    monkeypatch.setattr(n,"detect_magnitude_rect",lambda *a:None)
    monkeypatch.setattr(n,"locate_role_plots",
                        lambda hwnd:calls.append("fallback_uiA") or None)
    assert native_fit_worker(77,source,"blue",prior) is None
    assert calls==["fallback_uiA"]


def test_changed_source_identity_never_uses_old_role_cache(monkeypatch):
    _,_,source=model()
    fit=NativeMagFit(205,11.5,1.,.99,.2,200,True,"verified")
    prior=FitFrame(source.revision,MAG,fit,"blue",time.monotonic(),
        77,WIN,source.source_identity,True,True,PHASE)
    changed=replace(source,source_identity="OTHER")
    monkeypatch.setattr(n.win32gui,"IsWindow",lambda hwnd:True)
    monkeypatch.setattr(n.win32gui,"IsIconic",lambda hwnd:False)
    monkeypatch.setattr(n,"locate_role_plots",lambda hwnd:None)
    monkeypatch.setattr(n,"capture_native_window",
                        lambda hwnd:(_ for _ in ()).throw(
                            AssertionError("no capture if geometry untrusted")))
    assert native_fit_worker(77,changed,"blue",prior) is None


def test_verified_frame_geometry_structure_backwards_compatible():
    f=FitFrame(1,MAG,object(),"red",time.monotonic())
    assert f.phase_plot is None


def test_current_engine_role_hint_skips_slow_uia_but_rechecks_native_pixels(monkeypatch):
    _,_,source=model()
    snap=Image.new("RGB",(1920,1040),"black")
    calls=dict(capture=0,detect=0,uia=0)
    monkeypatch.setattr(n.win32gui,"IsWindow",lambda hwnd:True)
    monkeypatch.setattr(n.win32gui,"IsIconic",lambda hwnd:False)
    monkeypatch.setattr(n.win32gui,"GetWindowRect",lambda hwnd:WIN)
    def capture(hwnd):
        calls["capture"]+=1
        return snap,WIN
    def detect(img,window,positions):
        calls["detect"]+=1
        assert positions==(PHASE,MAG)
        return MAG,1.
    monkeypatch.setattr(n,"capture_native_window",capture)
    monkeypatch.setattr(n,"detect_magnitude_rect",detect)
    monkeypatch.setattr(n,"locate_role_plots",
        lambda hwnd:calls.__setitem__("uia",calls["uia"]+1))
    monkeypatch.setattr(n,"fit_native_mag_grid",lambda *a,**kw:NS(
        accepted=True,confidence=1.,px_per_db=10.))
    monkeypatch.setattr(n,"saved_mag_grid_interval",lambda:3.)
    fit=NativeMagFit(200,10.,0.,.99,.1,200,True,"fresh source pixels")
    monkeypatch.setattr(n,"choose_color_fit",
        lambda *a,**kw:n.ColorFit("blue",fit,0.,True))
    result=native_fit_worker(77,source,role_hint=(PHASE,MAG))
    assert result is not None and result.phase_plot==PHASE
    assert result.identity_verified and result.plot==MAG
    assert calls==dict(capture=1,detect=1,uia=0)
