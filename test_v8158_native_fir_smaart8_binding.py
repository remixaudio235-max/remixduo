"""V8.158 FIR: bind strictly to Smaart 8 observer and verify V8 plot titles."""
import sys
from types import SimpleNamespace as NS
import fir_native_v846 as n
from test_v860_fir_native_smaart_smoothing import setup,MAG,PHASE,WIN
import smaart8_api3_readonly_v868 as edition
import smaart8_plot_profile_v868 as profile


def test_v8_fir_retries_responsive_inner_raster_and_aligns_phase(monkeypatch):
    src,calls,smooth=setup(monkeypatch)
    monkeypatch.setattr(edition,"process_smaart_major",lambda h:8)
    monkeypatch.setattr(profile,"detect_v8_profile",lambda image:(PHASE,MAG))
    fit=n.NativeMagFit(186.,11.,0.,.91,0.,224,True,"inner native source")
    seen=[]
    inset=int(round(MAG[2]*.0225))
    inner_mag=(MAG[0]+inset,MAG[1],MAG[2]-2*inset,MAG[3])
    inner_phase=(PHASE[0]+inset,PHASE[1],PHASE[2]-2*inset,PHASE[3])

    def choose(image,rect,*args,**kwargs):
        seen.append(tuple(rect))
        if tuple(rect)==inner_mag:
            return n.ColorFit("blue",fit,0.,True)
        return None

    def phasefit(image,rect,*args,**kwargs):
        assert tuple(rect)==inner_phase
        return 361.,.97

    monkeypatch.setattr(n,"choose_color_fit",choose)
    monkeypatch.setattr(n,"phase_native_fit",phasefit)
    frame=n.native_fir_frame(123,src,center_phase_top=330.,
        smooth_hint=(smooth.mag_oct,smooth.phase_oct))
    assert frame is not None and frame.phase_verified
    assert frame.mag==inner_mag
    assert frame.phase==inner_phase
    assert seen==[MAG,inner_mag]

def test_v8_phase_fir_uses_verified_smaart8_titles_not_suite(monkeypatch):
    src,calls,smooth=setup(monkeypatch)
    monkeypatch.setattr(edition,"process_smaart_major",lambda h:8)
    seen=[]
    monkeypatch.setattr(profile,"detect_v8_profile",
                        lambda image:(seen.append(image.size) or (PHASE,MAG)))
    monkeypatch.setattr(n,"detect_magnitude_rect",lambda *a:
                        (_ for _ in ()).throw(AssertionError("V9 title forbidden")))
    monkeypatch.setattr(n,"locate_role_plots",lambda *a:
                        (_ for _ in ()).throw(AssertionError("V9 UIA forbidden")))
    frame=n.native_fir_frame(123,src,center_phase_top=330.,
                             smooth_hint=(smooth.mag_oct,smooth.phase_oct))
    assert frame is not None
    assert frame.mag==MAG and frame.phase==PHASE
    assert frame.phase_verified and frame.phase_score>=.97
    assert calls["capture"]==1 and calls["phase"]==1
    assert seen

def test_v8_unrecognized_native_plot_stays_hold(monkeypatch):
    src,calls,smooth=setup(monkeypatch)
    monkeypatch.setattr(edition,"process_smaart_major",lambda h:8)
    monkeypatch.setattr(profile,"detect_v8_profile",lambda image:None)
    assert n.native_fir_frame(123,src,
        smooth_hint=(smooth.mag_oct,smooth.phase_oct)) is None
    assert "Smaart 8" in n.LAST_HOLD_REASON[0]
    assert calls["fit"]==0 and calls["phase"]==0

def test_fir_hwnd_uses_current_tick_and_rejects_switched_smaart(monkeypatch):
    monkeypatch.setattr(n.win32gui,"IsWindow",lambda h:h==808)
    monkeypatch.setattr(n.win32gui,"IsWindowVisible",lambda h:h==808)
    monkeypatch.setattr(n.win32gui,"IsIconic",lambda h:False)
    monkeypatch.setattr(n.win32gui,"GetForegroundWindow",lambda:808)
    monkeypatch.setattr(n.win32process,"GetWindowThreadProcessId",lambda h:(0,42))
    hub=NS(active="fir",workspace_visible=True,isVisible=lambda:True,
           engine=NS(observer=NS(hwnd=808)),_last_hwnd=808,
           fir=NS(_approved=(None,"digest")))
    view=NS(hub=hub,source=NS(identity="digest"),_last_allowed_reason=None)
    assert n.NativeFIROverlay._allowed(view)==808
    hub._last_hwnd=909
    assert n.NativeFIROverlay._allowed(view)==0

def test_fir_other_edition_not_misbound(monkeypatch):
    src,_,_=setup(monkeypatch)
    monkeypatch.setattr(edition,"process_smaart_major",lambda h:7)
    assert n.native_fir_frame(123,src) is None
    assert "edition" in n.LAST_HOLD_REASON[0]
