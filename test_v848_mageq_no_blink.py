"""V8.48: source-safe fast native Y follow and transient Data Bar scan QA."""
from types import SimpleNamespace
import time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from dataclasses import replace
import pytest

from test_v847_autoeq_bypass_grid import model
import native_eq_mag_v06 as n
from native_eq_mag_v06 import FitFrame
from smaart_native_mag_fit import NativeMagFit
from smaart_native_y_grid_v839 import NativeGridY
import live_sync_v7 as sync

PLOT=(252,539,1442,412)
WINDOW=(0,0,1920,1040)


def screenshot(source,shift=0.,*,draw=True):
    original_db=source.original_db
    f=source.freqs
    c=source.coh
    median=float(np.median(original_db))
    center=205.
    scale=11.5
    img=Image.new("RGB",(1920,1040),(0,0,0))
    if draw:
        d=ImageDraw.Draw(img)
        xs=np.rint(PLOT[2]*np.log(f/20.)/np.log(1000.)).astype(int)
        yy=np.rint(center-(original_db-median)*scale+shift).astype(int)
        for x,y,q in zip(xs,yy,c):
            if q>=.6 and 15<x<PLOT[2]-15 and 4<y<PLOT[3]-5:
                px,py=int(x+PLOT[0]),int(y+PLOT[1])
                d.ellipse((px-2,py-2,px+2,py+2),fill=(30,100,244))
    old=NativeMagFit(center,scale,median,1.,.3,200,True,"previous native verified")
    prior=FitFrame(source.revision,PLOT,old,"blue",time.monotonic()-.8,
                   77,WINDOW,source_identity=source.source_identity,
                   identity_verified=True,grid_agrees=True)
    grid=SimpleNamespace(accepted=True,confidence=1.,px_per_db=11.5)
    return img,prior,grid


def test_fast_revalidation_on_new_pixels_reanchors_Y_and_does_not_reuse_stale_timestamp():
    _,_,s=model()
    img,prior,grid=screenshot(s,shift=0.)
    first=n._fast_refit_same_source(img,PLOT,WINDOW,s,grid,prior)
    assert first and first.identity_verified
    assert first.fit.score>=.86
    assert first.created>prior.created
    shifted,_,_=screenshot(s,shift=26.)
    second=n._fast_refit_same_source(shifted,PLOT,WINDOW,s,grid,first)
    assert second and second.created>=first.created
    assert abs((second.fit.center_px-first.fit.center_px)-26.)<=2.1
    assert second.fit.px_per_db>0


def test_native_new_pixels_required_and_source_identity_never_reused():
    _,_,s=model()
    img,prior,grid=screenshot(s)
    blank,_,_=screenshot(s,draw=False)
    assert n._fast_refit_same_source(blank,PLOT,WINDOW,s,grid,prior) is None
    assert n._fast_refit_same_source(img,PLOT,WINDOW,
                 replace(s,source_identity="changed"),grid,prior) is None
    assert n._fast_refit_same_source(img,PLOT,(0,0,1200,900),s,
                                    grid,prior) is None
    assert n._fast_refit_same_source(img,PLOT,WINDOW,s,
            SimpleNamespace(accepted=False,confidence=0,px_per_db=11.5),
            prior) is None


def test_transient_scan_suspends_display_not_source_identity(tmp_path):
    observer_cls=next(v for v in vars(sync).values()
                      if isinstance(v,type) and
                      callable(getattr(v,"suspend_single_transient",None)))
    obs=observer_cls.__new__(observer_cls)
    f=tmp_path/"one.trf"
    f.write_bytes(b"saved only")
    candidate=(str(f),f.stat().st_mtime_ns,f.stat().st_size)
    obs.ready=True
    obs.order=[f]
    obs.states={0:"on"}
    obs.single_candidate=candidate
    obs.single_stable=3
    obs.single_generation=23
    obs.single_tick=(*candidate,23)
    obs.single_verified_at=time.perf_counter()
    obs.single_scan_at=obs.single_verified_at
    obs.row_seen_at={0:obs.single_verified_at}
    assert obs.current_single()==(*candidate,23)
    obs.suspend_single_transient()
    assert obs.current_single() is None
    assert obs.single_candidate==candidate
    assert obs.single_generation==23
    for i in range(3):
        obs.observe_single(time.perf_counter())
    assert obs.current_single()==(*candidate,23)
    # Proven tick changed to a new file: generation changes, stale EQ fails.
    other=tmp_path/"other.trf"
    other.write_bytes(b"other")
    obs.order=[other]
    obs.observe_single(time.perf_counter())
    assert obs.current_single() is None
    assert obs.single_generation>23


def test_EQ_dialog_does_not_discard_approved_result_on_transient_scan(monkeypatch):
    from PyQt6.QtWidgets import QApplication
    from overlay_v7 import App
    from signal_tools_gui_v813 import EQDialog
    app=QApplication.instance() or QApplication([])
    source,_,_=model()
    token=(str(source),source.stat().st_mtime_ns,source.stat().st_size,12)
    obs=SimpleNamespace(single_candidate=token[:3],ready=True,
                        order=[source],states={0:"on"},single_scan_at=0.)
    engine=App(False)
    engine.timer.stop()
    engine.observer=obs
    dlg=EQDialog(engine)
    try:
        dlg._single_token=token
        dlg._eq_state=(token,1)
        dlg.source.clear()
        dlg.source.addItem("saved",0)
        dlg.result=object()
        monkeypatch.setattr(dlg,"_verified_single",lambda:None)
        monkeypatch.setattr(dlg,"_refresh_fs",lambda *a,**kw:None)
        dlg.refresh_sources()
        assert dlg.result is not None
        assert dlg._single_token==token
        assert dlg.source.currentData()==0
        obs.single_candidate=("other",0,0)
        dlg.refresh_sources()
        assert dlg.result is None
    finally:
        dlg._pool.shutdown(wait=False,cancel_futures=True)
        dlg.close()
        engine.close()



def test_static_many_native_frames_never_accumulate_center_drift():
    _,_,src=model()
    image,prior,grid=screenshot(src)
    first=None
    for i in range(12):
        frame=n._fast_refit_same_source(image,PLOT,WINDOW,src,grid,prior)
        assert frame is not None, f"static frame {i}: no verified match"
        if first is None:first=frame.fit.center_px
        assert abs(frame.fit.center_px-first)<2.,f"Y center drift at frame {i}"
        assert frame.identity_verified and frame.grid_agrees
        prior=frame
    moved,_,_=screenshot(src,shift=26.)
    new=n._fast_refit_same_source(moved,PLOT,WINDOW,src,grid,prior)
    assert new is not None
    assert abs(new.fit.center_px-prior.fit.center_px-26.)<=2.1
