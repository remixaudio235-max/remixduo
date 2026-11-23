"""V8.46 FIR complex parity, native Mag/Phase source-match, overlay sharing."""
import os,time
os.environ["QT_QPA_PLATFORM"]="offscreen"
from pathlib import Path
import numpy as np
import scipy.signal
from PIL import Image,ImageDraw
from dataclasses import replace
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from fir_native_v846 import (
    make_source,FIRFrame,phase_native_fit,fir_mag_points,
    fir_phase_points,native_fir_fresh)
from smaart_native_mag_fit import NativeMagFit
from signal_tools_core_v813 import design_linear_phase_fir
from overlay_v7 import App
from test_v845_fir_one_trace import init,wait_fir

MAG=(252,539,1442,412)
PHASE=(252,84,1442,412)
WIN=(0,0,1920,1080)


def source():
    f=np.geomspace(20.,20000.,1400)
    h=np.ones(f.size,complex)*10**(-7/20)
    coh=np.ones_like(f)
    r=design_linear_phase_fir(f,h,coh,512,48000,source="QA")
    return make_source(f,h,coh,r.taps,48000,"QA","digest",2),r


def frame(src,*,verified=True,mag_fit=None,phase_top=180):
    if mag_fit is None:
        mag_fit=NativeMagFit(170.,11.5,-7.,.96,.2,180,True,"pixel match")
    return FIRFrame(src.revision,src.identity,123,WIN,MAG,PHASE,mag_fit,
                    float(phase_top),360.,.95 if verified else 0.,"red",
                    time.monotonic(),verified)


def test_complex_fir_convolution_phase_delay_retained_and_mag_correct():
    src,r=source()
    _,H=scipy.signal.freqz(r.taps,worN=src.freqs,fs=48000)
    expected=20*np.log10(np.maximum(abs(H),1e-12))
    assert np.allclose(src.after_db-src.original_db,expected,atol=.0001)
    # For a flat original H the phase difference is exactly FIR phase,
    # including uncompensated linear-phase group delay.
    intended=np.angle(H)
    actual=np.deg2rad(src.after_phase-src.original_phase)
    reliable=src.phase_valid&(abs(H)>.005)
    assert reliable.sum()>200
    assert np.max(abs(np.angle(np.exp(1j*(actual[reliable]-intended[reliable])))))<1e-7


def test_shared_native_frame_translates_mag_and_wraps_phase():
    src,_=source()
    fr=frame(src)
    mag,valid=fir_mag_points(src,fr)
    ph,pvalid=fir_phase_points(src,fr)
    assert len(mag)==len(ph)==len(src.freqs)
    assert np.count_nonzero(valid)>100 and np.count_nonzero(pvalid)>100
    translated=frame(src,mag_fit=replace(fr.mag_fit,center_px=fr.mag_fit.center_px+31.))
    moved,_=fir_mag_points(src,translated)
    assert np.allclose(moved[:,1]-mag[:,1],31.,atol=1e-7)
    shifted=frame(src,phase_top=fr.phase_top+25)
    newphase,_=fir_phase_points(src,shifted)
    delta=(newphase[:,1]-ph[:,1])%PHASE[3]
    assert np.allclose(delta,PHASE[3]*25/360,atol=1e-7)


def test_phase_fit_requires_source_colored_pixels_not_mag_only():
    src,_=source()
    im=Image.new("RGB",(1920,1080),(6,10,16))
    assert phase_native_fit(im,PHASE,WIN,src,"red") is None
    # Build a synthetic Smaart-original red Phase curve of the SAME TRF.
    # Only unit-score native source phase can authorize PhaseFIR.
    d=ImageDraw.Draw(im)
    x0,y0,w,h=PHASE
    p=src.original_phase
    hz=src.freqs
    points=[]
    for i in range(len(hz)):
        x=w*np.log(hz[i]/20.)/np.log(1000.)
        y=((180-p[i])%360)*h/360.
        if (50<x<w-360) and (1<y<h-2) and src.phase_valid[i]:
            points.append((int(x0+x),int(y0+y)))
    for x,y in points:d.ellipse((x-2,y-2,x+2,y+2),fill=(245,45,16))
    fit=phase_native_fit(im,PHASE,WIN,src,"red",center_top=180.)
    assert fit is not None
    assert abs(((fit[0]-180+180)%360)-180)<12
    assert fit[1]>=.78
    assert phase_native_fit(im,PHASE,WIN,src,"blue") is None


def test_native_fir_expiry_wrong_source_window_or_plot(monkeypatch):
    import native_eq_mag_v06
    monkeypatch.setattr(native_eq_mag_v06.win32gui,"IsWindow",lambda h:True)
    monkeypatch.setattr(native_eq_mag_v06.win32gui,"IsIconic",lambda h:False)
    monkeypatch.setattr(native_eq_mag_v06.win32gui,"GetWindowRect",lambda h:WIN)
    src,_=source()
    fr=frame(src)
    assert native_fir_fresh(fr,src,123,MAG,PHASE,now=fr.created+.1)
    assert not native_fir_fresh(fr,src,123,MAG,PHASE,now=fr.created+1.)
    assert not native_fir_fresh(fr,src,123,(220,539,1442,412),PHASE,
                                now=fr.created+.1)
    assert not native_fir_fresh(fr,src,124,MAG,PHASE,now=fr.created+.1)
    assert not native_fir_fresh(fr,replace(src,identity="wrong"),123,
                                MAG,PHASE,now=fr.created+.1)


def test_same_existing_qt_plot_widgets_and_click_through():
    app=QApplication.instance() or QApplication([])
    src,_=source()
    fr=frame(src)
    engine=App(False)
    engine.timer.stop()
    gmag,gph=engine.graph_mag,engine.graph_phase
    gmag.setGeometry(*MAG)
    gph.setGeometry(*PHASE)
    try:
        gmag.set_fir(src,fr)
        gph.set_fir(src,fr)
        gmag.show();gph.show()
        app.processEvents()
        for graph in (gmag,gph):
            assert graph.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            assert bool(graph.windowFlags() & Qt.WindowType.WindowTransparentForInput)
            assert graph.fir_source is src and graph.fir_frame is fr
            assert graph.grab().toImage().width()>1000
        assert engine.graph_mag is gmag and engine.graph_phase is gph
        # Native phase proof is independent: MAG may remain, PHASE HOLD.
        hold=replace(fr,phase_verified=False)
        gph.set_fir(src,hold)
        app.processEvents()
        assert not fir_phase_points(src,hold)[0].size
        gmag.set_fir();gph.set_fir()
        assert gmag.fir_source is None and gph.fir_source is None
    finally:
        gmag.close();gph.close();engine.close()


def test_fir_dialog_worker_connects_native_preview_without_smaart():
    app,obs,engine,hub,fir=init()
    try:
        # This test checks the native magnitude preview; explicitly use MAG.
        fir.fir_mag_button.click()
        fir.compute()
        wait_fir(app,fir)
        assert fir.result is not None
        assert hub.native_fir.source is not None
        assert hub.native_fir.source.source_name==fir.result.source
        assert hub.native_fir.frame is None
        assert fir.plot.isHidden()  # native plot overlay is the only FIR graph
        assert "HOLD" in fir.overlay_status.text()
        assert engine.graph_mag.fir_source is None
        assert engine.graph_phase.fir_source is None
        # On leaving FIR mode, all native FIR model layers are hidden.
        hub.select("eq")
        app.processEvents()
        assert engine.graph_mag.fir_source is None
        assert engine.graph_phase.fir_source is None
    finally:
        hub.close();app.processEvents()



def test_native_shared_frame_requires_mag_source_and_phase_independent(monkeypatch):
    from types import SimpleNamespace
    import fir_native_v846 as n
    app,obs,engine,hub,fir=init()
    try:
        fir.fir_mag_button.click()
        fir.compute()
        wait_fir(app,fir)
        src=hub.native_fir.source
        assert src is not None
        engine.plot_layout=SimpleNamespace(mag=MAG,phase=PHASE)
        engine.overlay_positioned=True
        engine._apply_plot_layout()
        monkeypatch.setattr(hub.native_fir,"_allowed",lambda:123)
        monkeypatch.setattr(n,"native_fir_fresh",lambda *a,**k:True)
        f=frame(src)
        hub.native_fir.frame=f
        hub.native_fir._publish()
        assert engine.graph_mag.fir_source is src
        assert engine.graph_phase.fir_source is None
        assert fir.overlay_status.text()=="MagFIR PASS | PhaseFIR OFF"
        bad=replace(f,phase_verified=False)
        hub.native_fir.frame=bad
        hub.native_fir._publish()
        assert engine.graph_mag.fir_frame is bad
        assert engine.graph_phase.fir_source is None
        assert fir.overlay_status.text()=="MagFIR PASS | PhaseFIR OFF"
        # V8.62 phase mode uses only the Phase layer and requires independent
        # phase pixels, even when the magnitude registration is accepted.
        phase_source=replace(src,mode='phase')
        hub.native_fir.source=phase_source
        hub.native_fir.frame=f
        hub.native_fir._publish()
        assert engine.graph_mag.fir_source is None
        assert engine.graph_phase.fir_source is phase_source
        hub.native_fir.frame=bad
        hub.native_fir._publish()
        assert engine.graph_phase.fir_source is None
        assert fir.overlay_status.text()=="MagFIR OFF | PhaseFIR HOLD"
        # Losing native Mag proof removes BOTH layers at the same time.
        monkeypatch.setattr(n,"native_fir_fresh",lambda *a,**k:False)
        hub.native_fir._publish()
        assert engine.graph_mag.fir_source is None
        assert engine.graph_phase.fir_source is None
    finally:
        hub.close();app.processEvents()


def test_worker_phase_raster_is_real_and_deterministic():
    from fir_native_v846 import rasterize_fir_frame
    src,_=source()
    fr=rasterize_fir_frame(src,frame(src))
    assert isinstance(fr.mag_raster,bytes)
    assert isinstance(fr.phase_raster,bytes)
    assert len(fr.mag_raster)==MAG[2]*MAG[3]*4
    assert len(fr.phase_raster)==PHASE[2]*PHASE[3]*4
    rgba=np.frombuffer(fr.phase_raster,dtype=np.uint8).reshape(
        PHASE[3],PHASE[2],4)
    assert (rgba[:,:,3]>0).sum()>1000
    hold=rasterize_fir_frame(src,replace(fr,phase_verified=False))
    assert hold.phase_raster is None and hold.mag_raster is not None
