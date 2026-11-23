"""V8.40 AutoEQ native-grid integration: one source, one Mag plot, PEQ UI.

Read-only tests; original Smaart transfer-function files remain untouched.
"""
from pathlib import Path
from types import SimpleNamespace
import time

import numpy as np
from PIL import Image
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
import pytest

import native_eq_mag_v06 as native
from native_eq_mag_v06 import build_state, FitFrame, native_fit_worker
from overlay_v7 import SumGraph
from smaart_native_mag_fit import NativeMagFit
from mageq_visual_v13 import build_geometry

HERE=Path(__file__).parent
SCREEN=HERE/"QA_V837_LIVE_AFTER_SCREEN.png"
RECT=(252,539,1442,412)
WINDOW=(0,0,1920,1080)


def source():
    f=np.geomspace(20.,20000.,1800)
    h=np.ones_like(f,dtype=np.complex128)*10**(-9/20)
    coh=np.ones_like(f)
    peqs=tuple(SimpleNamespace(freq_hz=fc,gain_db=db,q=q)
        for fc,db,q in ((75.,2.,1.5),(295.,-1.7,16.),
                        (944.,-4.2,1.95),(715.,-1.65,8.)))
    return build_state(f,h,coh,peqs,fs=48000,source_index=0,
        source_name="0 delay-2",revision=17)


def test_native_grid_without_matching_original_trace_is_rejected(monkeypatch):
    src=source()
    monkeypatch.setattr(native.win32gui,"IsWindow",lambda hwnd:True)
    monkeypatch.setattr(native.win32gui,"IsIconic",lambda hwnd:False)
    monkeypatch.setattr(native,"locate_role_plots",
        lambda hwnd:SimpleNamespace(phase=(252,84,1442,412),mag=RECT))
    monkeypatch.setattr(native,"capture_native_window",
        lambda hwnd:(Image.open(SCREEN).convert("RGB"),WINDOW))
    monkeypatch.setattr(native,"detect_magnitude_rect",
        lambda image,window,positions:(RECT,1.))
    monkeypatch.setattr(native,"choose_color_fit",
        lambda *args,**kwargs:None)
    monkeypatch.setattr(native,"saved_mag_grid_interval",lambda:3.)
    assert native_fit_worker(12345,src) is None


def test_source_pixel_identity_and_grid_share_one_native_frame(monkeypatch):
    from smaart_eq_color_select import ColorFit
    src=source()
    monkeypatch.setattr(native.win32gui,"IsWindow",lambda hwnd:True)
    monkeypatch.setattr(native.win32gui,"IsIconic",lambda hwnd:False)
    monkeypatch.setattr(native,"locate_role_plots",
        lambda hwnd:SimpleNamespace(phase=(252,84,1442,412),mag=RECT))
    monkeypatch.setattr(native,"capture_native_window",
        lambda hwnd:(Image.open(SCREEN).convert("RGB"),WINDOW))
    monkeypatch.setattr(native,"detect_magnitude_rect",
        lambda image,window,positions:(RECT,1.))
    monkeypatch.setattr(native,"choose_color_fit",
        lambda *args,**kwargs:ColorFit(
            "red",NativeMagFit(171.,11.5,0.,.94,0.,110,True,
                               "matched original native Mag"),0.,True))
    monkeypatch.setattr(native,"saved_mag_grid_interval",lambda:3.)
    frame=native_fit_worker(12345,src)
    assert frame and frame.identity_verified
    assert frame.source_identity==src.source_identity
    assert frame.revision==src.revision and frame.plot==RECT
    assert frame.hwnd==12345 and frame.window_rect==WINDOW
    assert frame.fit.score>=.90
    geo=build_geometry(src,frame)
    assert len(geo.markers)==4 and len(geo.spans)>0


def test_mageq_markers_gradient_and_line_render_same_native_plot():
    app=QApplication.instance() or QApplication([])
    assert app is not None
    src=source()
    fit=NativeMagFit(171.,11.5,0.,1.,0.,0,True,"native 0dB grid")
    frame=FitFrame(src.revision,RECT,fit,"GRID",time.monotonic())
    graph=SumGraph("mag")
    graph.setGeometry(*RECT)
    graph.set_mageq(src,frame)
    graph.show()
    app.processEvents()
    try:
        img=graph.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        assert img.width()==RECT[2] and img.height()==RECT[3]
        stats=graph.mageq_annotation_stats
        assert graph.mageq_draw_count>=1
        assert stats["total_peq"]==4
        assert stats["markers"]==4
        assert stats["gradients"]>0
        bits=img.bits();bits.setsize(img.sizeInBytes())
        ar=np.frombuffer(bits,dtype=np.uint8).reshape(img.height(),img.width(),4)
        assert np.count_nonzero(ar[:,:,3])>1000
    finally:
        graph.close()


def test_unknown_grid_and_unmatched_curve_fail_closed(monkeypatch):
    src=source()
    monkeypatch.setattr(native.win32gui,"IsWindow",lambda hwnd:True)
    monkeypatch.setattr(native.win32gui,"IsIconic",lambda hwnd:False)
    monkeypatch.setattr(native,"locate_role_plots",
        lambda hwnd:SimpleNamespace(phase=(252,84,1442,412),mag=RECT))
    monkeypatch.setattr(native,"capture_native_window",
        lambda hwnd:(Image.open(SCREEN).convert("RGB"),WINDOW))
    monkeypatch.setattr(native,"detect_magnitude_rect",
        lambda image,window,positions:(RECT,1.))
    monkeypatch.setattr(native,"saved_mag_grid_interval",lambda:None)
    monkeypatch.setattr(native,"choose_color_fit",lambda *a,**k:None)
    assert native_fit_worker(999,src) is None


def test_mismatched_mag_role_rejected(monkeypatch):
    src=source()
    monkeypatch.setattr(native.win32gui,"IsWindow",lambda hwnd:True)
    monkeypatch.setattr(native.win32gui,"IsIconic",lambda hwnd:False)
    monkeypatch.setattr(native,"locate_role_plots",
        lambda hwnd:SimpleNamespace(phase=(252,84,1442,412),mag=RECT))
    monkeypatch.setattr(native,"capture_native_window",
        lambda hwnd:(Image.open(SCREEN).convert("RGB"),WINDOW))
    monkeypatch.setattr(native,"detect_magnitude_rect",
        lambda image,window,positions:((252,84,1442,412),.99))
    assert native_fit_worker(777,src) is None
