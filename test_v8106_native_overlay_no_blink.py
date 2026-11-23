"""V8.106: MagEQ/FIR native overlay must not blink on recompute or capture lag.

Measured on the live 1920x1040 Smaart window (read-only, 2026-11-04):
UIA locate_role_plots 335 ms (max 620), PrintWindow 155 ms, Mag grid fit
134 ms. A verification therefore takes ~0.3-0.4 s, so a frame with a 0.45 s
TTL often expired before its successor landed (curve blink), and every
Auto EQ / FIR recompute discarded the geometry seed (full UIA rescan).
"""
import os,time
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from types import SimpleNamespace as NS
import numpy as np
import pytest

import native_eq_mag_v06 as N
import fir_native_v846 as F
from smaart_native_mag_fit import NativeMagFit
from smaart_eq_color_select import ColorFit

HWND=123
WIN=(0,0,1920,1040)
MAG=(252,539,1442,412)
PHASE=(252,84,1442,412)
GOOD_FIT=NativeMagFit(170.,11.5,-7.,.96,.2,180,True,"pixel match")


class FakeWin32:
    def __init__(self,rect=WIN):
        self.rect=rect
    def IsWindow(self,h):return True
    def IsIconic(self,h):return False
    def GetWindowRect(self,h):return self.rect


def _no_uia(*a,**k):
    raise AssertionError("full UIA rescan called although geometry seed is valid")


def mag_prior(*,identity="A",revision=1,color="red",age=0.):
    return N.FitFrame(revision,MAG,GOOD_FIT,color,time.monotonic()-age,HWND,WIN,
                      source_identity=identity,identity_verified=True,
                      grid_agrees=True,phase_plot=PHASE)


def mag_source(*,identity="A",revision=2):
    f=np.geomspace(20.,20000.,400)
    return NS(source_identity=identity,revision=revision,freqs=f,
              original_db=np.zeros_like(f),coh=np.ones_like(f))


@pytest.fixture
def native_env(monkeypatch):
    calls={"fit_native_mag":[],"choose":0}
    monkeypatch.setattr(N,"win32gui",FakeWin32())
    monkeypatch.setattr(N,"locate_role_plots",_no_uia)
    monkeypatch.setattr(N,"capture_native_window",lambda h:("IMG",WIN))
    monkeypatch.setattr(N,"detect_magnitude_rect",lambda img,win,rects:(rects[1],rects[0]))
    monkeypatch.setattr(N,"saved_mag_grid_interval",lambda:10.)
    monkeypatch.setattr(N,"fit_native_mag_grid",
        lambda *a:NS(accepted=True,confidence=.99,px_per_db=11.5))
    monkeypatch.setattr(N,"_fast_refit_same_source",lambda *a:None)
    def fake_fit(*a,trace_color=None,**k):
        calls["fit_native_mag"].append(trace_color)
        return GOOD_FIT
    def fake_choose(*a,**k):
        calls["choose"]+=1
        return ColorFit("cyan",GOOD_FIT,0.,True)
    monkeypatch.setattr(N,"fit_native_mag",fake_fit)
    monkeypatch.setattr(N,"choose_color_fit",fake_choose)
    return calls


def test_mageq_recompute_same_trace_reuses_geometry_and_color(native_env):
    # Auto EQ recompute: same original measurement, new revision.
    frame=N.native_fit_worker(HWND,mag_source(revision=2),"red",mag_prior(revision=1))
    assert frame is not None and frame.revision==2 and frame.plot==MAG
    assert frame.phase_plot==PHASE and frame.color=="red"
    assert native_env["fit_native_mag"]==["red"] and native_env["choose"]==0


def test_mageq_new_trace_never_inherits_cache_or_color(native_env):
    # V8.53 contract kept: a different measurement needs full UIA + color scan.
    with pytest.raises(AssertionError,match="UIA"):
        N.native_fit_worker(HWND,mag_source(identity="B"),"red",mag_prior(identity="A"))
    assert native_env["fit_native_mag"]==[]


def test_mageq_seed_color_miss_holds_this_capture(native_env,monkeypatch):
    # V8.47 contract kept: a miss never silently proves another color.
    def miss(*a,trace_color=None,**k):
        native_env["fit_native_mag"].append(trace_color)
        return NativeMagFit(0.,1.,0.,.1,.9,10,False,"no match")
    monkeypatch.setattr(N,"fit_native_mag",miss)
    monkeypatch.setattr(N,"fit_native_mag_grid",
        lambda *a:NS(accepted=False,confidence=0.,px_per_db=11.5))
    assert N.native_fit_worker(HWND,mag_source(),"red",mag_prior()) is None
    assert native_env["choose"]==0


def test_mageq_moved_window_still_requires_full_rescan(native_env,monkeypatch):
    monkeypatch.setattr(N,"win32gui",FakeWin32((10,10,1930,1050)))
    with pytest.raises(AssertionError,match="UIA"):
        N.native_fit_worker(HWND,mag_source(),"red",mag_prior())


@pytest.mark.parametrize("age,verifying,expected",[
    (.30,False,True),(.30,True,True),
    (.60,True,True),(.60,False,False),
    (.95,True,True),(1.55,True,False)])
def test_display_grace_only_while_verification_in_flight(monkeypatch,age,verifying,expected):
    monkeypatch.setattr(N,"win32gui",FakeWin32())
    assert N.NATIVE_DISPLAY_GRACE_S==1.50
    f=mag_prior(age=age)
    assert N.frame_presentable(f,HWND,verifying=verifying)==expected
    # Export/drag gate is unchanged and strict.
    assert N.frame_is_fresh_for_window(f,HWND)==(age<=N.NATIVE_FRAME_MAX_AGE_S)


def test_display_grace_never_survives_window_move(monkeypatch):
    monkeypatch.setattr(N,"win32gui",FakeWin32((5,0,1925,1040)))
    assert not N.frame_presentable(mag_prior(age=.05),HWND,verifying=True)


def test_mageq_clear_keeps_seed_but_drops_display():
    seed=mag_prior()
    fake=NS(revision=4,approved_token=("t",),_last_verified_color="red",
            _last_verified_frame=seed,source=object(),frame=seed,
            _sync_sum_renderer=lambda:None,hide=lambda:None,update=lambda:None)
    N.NativeAutoEQMag.clear(fake)
    assert fake.source is None and fake.frame is None and fake.revision==5
    assert fake._last_verified_frame is seed and fake._last_verified_color=="red"


class DoneFuture:
    def __init__(self,value):self.value=value
    def done(self):return True
    def result(self):return self.value


class PendingFuture:
    def done(self):return False


def _mag_tick_self(monkeypatch,frame,future,failed=False):
    monkeypatch.setattr(N,"win32gui",NS(FindWindow=lambda *a:HWND,
        IsWindowVisible=lambda h:True,IsIconic=lambda h:False,
        IsWindow=lambda h:True,GetWindowRect=lambda h:WIN,
        GetForegroundWindow=lambda:HWND))
    monkeypatch.setattr(N,"win32process",NS(GetWindowThreadProcessId=lambda h:(1,77)))
    hub=NS(active="eq",isVisible=lambda:True,workspace_visible=True,
           engine=NS(observer=NS(hwnd=HWND)),_last_hwnd=HWND,
           _eq_tick_safe=lambda:True)
    fake=NS(source=NS(revision=frame.revision,source_identity="A"),enabled=True,
            hub=hub,frame=frame,future=future,_verify_failed=failed,
            last_submit=time.monotonic(),last_native_drop="",
            _last_verified_color="red",_last_verified_frame=frame,
            pool=NS(submit=lambda *a,**k:PendingFuture()),
            _source_binding_ok=lambda **k:True,_sync_sum_renderer=lambda:None,
            isVisible=lambda:False,hide=lambda:None)
    fake._presentable=lambda f,h:N.NativeAutoEQMag._presentable(fake,f,h)
    return fake


def test_mageq_tick_keeps_frame_while_successor_capture_in_flight(monkeypatch):
    frame=mag_prior(revision=2,age=.60)
    fake=_mag_tick_self(monkeypatch,frame,PendingFuture())
    N.NativeAutoEQMag.tick(fake)
    assert fake.frame is frame


def test_mageq_tick_keeps_aged_frame_after_one_failed_verification(monkeypatch):
    frame=mag_prior(revision=2,age=.60)
    fake=_mag_tick_self(monkeypatch,frame,DoneFuture(None))
    N.NativeAutoEQMag.tick(fake)
    assert fake.frame is frame and fake._verify_failed
    assert fake._last_verified_color=="red"  # one miss keeps the seed


def test_mageq_repeated_failures_drop_seed_for_full_rescan(monkeypatch):
    frame=mag_prior(revision=2,age=.60)
    fake=_mag_tick_self(monkeypatch,frame,DoneFuture(None))
    for _ in range(N.SEED_DROP_AFTER_FAILURES):
        fake.future=DoneFuture(None)
        N.NativeAutoEQMag.tick(fake)
    assert fake._last_verified_color is None and fake._last_verified_frame is None
    assert fake.frame is None


# ---------------- FIR ----------------

def fir_source(identity="digest",revision=3):
    f=np.geomspace(20.,20000.,400)
    return NS(identity=identity,revision=revision,freqs=f,original_db=np.zeros_like(f),
              coherence=np.ones_like(f),mode="mag")


def fir_prior(identity="digest",revision=2,color="red",age=0.):
    return F.FIRFrame(revision,identity,HWND,WIN,MAG,PHASE,GOOD_FIT,180.,360.,.9,
                      color,time.monotonic()-age,False)


@pytest.fixture
def fir_env(monkeypatch):
    calls={"fit":[],"choose":0}
    smooth=NS(mag_verified=True,mag_oct=1/6,phase_verified=False,phase_oct=0.)
    monkeypatch.setattr(F,"win32gui",FakeWin32())
    monkeypatch.setattr(F,"locate_role_plots",_no_uia)
    monkeypatch.setattr(F,"capture_native_window",lambda h:("IMG",WIN))
    monkeypatch.setattr(F,"detect_magnitude_rect",lambda img,win,rects:(rects[1],rects[0]))
    monkeypatch.setattr(F,"read_saved_smooth",lambda:smooth)
    monkeypatch.setattr(F,"saved_mag_grid_interval",lambda:10.)
    monkeypatch.setattr(F,"fit_native_mag_grid",
        lambda *a:NS(accepted=True,confidence=.99,px_per_db=11.5))
    monkeypatch.setattr(F,"rasterize_fir_frame",lambda src,frame:frame)
    def fake_fit(*a,trace_color=None,**k):
        calls["fit"].append(trace_color);return GOOD_FIT
    def fake_choose(*a,**k):
        calls["choose"]+=1;return ColorFit("cyan",GOOD_FIT,0.,True)
    monkeypatch.setattr(F,"fit_native_mag",fake_fit)
    monkeypatch.setattr(F,"choose_color_fit",fake_choose)
    return calls


def test_fir_recompute_same_trace_reuses_geometry_and_color(fir_env):
    frame=F.native_fir_frame(HWND,fir_source(revision=3),180.,fir_prior(revision=2))
    assert frame is not None and frame.revision==3 and frame.mag==MAG
    assert fir_env["fit"]==["red"] and fir_env["choose"]==0


def test_fir_new_trace_never_inherits_cache(fir_env):
    with pytest.raises(AssertionError,match="UIA"):
        F.native_fir_frame(HWND,fir_source(identity="other"),180.,fir_prior())


def test_fir_repeated_failures_drop_seed(monkeypatch):
    monkeypatch.setattr(N,"win32gui",FakeWin32())
    frame=fir_prior(revision=2)
    fake=_fir_tick_self(frame,DoneFuture(None),fir_source(revision=2))
    for _ in range(N.SEED_DROP_AFTER_FAILURES):
        fake.future=DoneFuture(None)
        F.NativeFIROverlay.tick(fake)
    assert fake.last_verified is None


def test_fir_clear_and_accept_keep_geometry_seed(monkeypatch):
    seed=fir_prior()
    fake=NS(source=object(),frame=seed,last_verified=seed,future=object(),
            last_submit=5.,_publish=lambda:None,tick=lambda:None)
    F.NativeFIROverlay.clear(fake)
    assert fake.frame is None and fake.last_verified is seed
    monkeypatch.setattr(F,"QTimer",NS(singleShot=lambda *a:None))
    F.NativeFIROverlay.accept(fake,fir_source())
    assert fake.frame is None and fake.last_verified is seed


def _fir_tick_self(frame,future,src):
    fake=NS(source=src,frame=frame,future=future,_verify_failed=False,
            last_submit=time.monotonic(),last_verified=frame,
            hub=NS(engine=NS(graph_phase=NS(y_max=180.))),
            pool=NS(submit=lambda *a,**k:PendingFuture()),
            _allowed=lambda:HWND,_publish=lambda:None,
            _toast_hold_reason=lambda:None)
    fake._presentable=(lambda f,h,m=None,p=None:
                       F.NativeFIROverlay._presentable(fake,f,h,m,p))
    return fake


def test_fir_tick_keeps_frame_while_successor_capture_in_flight(monkeypatch):
    monkeypatch.setattr(N,"win32gui",FakeWin32())
    src=fir_source(revision=2)
    frame=fir_prior(revision=2,age=.60)
    fake=_fir_tick_self(frame,PendingFuture(),src)
    F.NativeFIROverlay.tick(fake)
    assert fake.frame is frame


def test_fir_display_grace_covers_measured_native_fit_without_blink(monkeypatch):
    """A 1.8 s Suite fit must not blank the last independently verified line."""
    monkeypatch.setattr(N,"win32gui",FakeWin32())
    src=fir_source(revision=2)
    frame=fir_prior(revision=2,age=1.80)
    fake=_fir_tick_self(frame,PendingFuture(),src)
    F.NativeFIROverlay.tick(fake)
    assert F.FIR_DISPLAY_GRACE_S>=1.80
    assert fake.frame is frame


def test_fir_tick_preserves_verified_frame_while_panel_hidden():
    """Dock visibility is a proof pause, never a reason to erase valid FIR."""
    frame=fir_prior(revision=2,age=.60)
    fake=NS(frame=frame,_last_allowed_reason="hub_hidden",
            _allowed=lambda:0,_publish=lambda:None)
    F.NativeFIROverlay.tick(fake)
    assert fake.frame is frame


def test_fir_publish_does_not_downgrade_pass_during_transient_block():
    frame=fir_prior(revision=2,age=.60)
    calls=[]
    engine=NS(refresh_visibility=lambda:calls.append("refresh"))
    fake=NS(source=fir_source(revision=2),frame=frame,
            hub=NS(engine=engine),_last_allowed_reason="hub_hidden",
            _allowed=lambda:0)
    F.NativeFIROverlay._publish(fake)
    assert calls==["refresh"]


def test_fir_tick_keeps_aged_frame_after_one_failed_verification(monkeypatch):
    monkeypatch.setattr(N,"win32gui",FakeWin32())
    src=fir_source(revision=2)
    frame=fir_prior(revision=2,age=.60)
    fake=_fir_tick_self(frame,DoneFuture(None),src)
    F.NativeFIROverlay.tick(fake)
    assert fake.frame is frame and fake._verify_failed


def test_fir_third_failed_verification_drops_frame_and_seed(monkeypatch):
    monkeypatch.setattr(N,"win32gui",FakeWin32())
    src=fir_source(revision=2)
    frame=fir_prior(revision=2,age=.60)
    fake=_fir_tick_self(frame,DoneFuture(None),src)
    for _ in range(N.SEED_DROP_AFTER_FAILURES):
        fake.future=DoneFuture(None)
        F.NativeFIROverlay.tick(fake)
    assert fake.frame is None and fake.last_verified is None
