"""R60: dark olive native Smaart8 source is an actual, visible trace.

Requires a read-only captured native lab frame for the integration tests.
Never changes Smaart's soundcard, generator, trace selection or DSP.
"""
import os
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from smaart_native_mag_fit import trace_color_mask,NativeMagFrame
from mag_sum_native_v826 import _smaart8_native_source_axis
from smaart8_native_xaxis_v8172 import select_smaart8_native_axis
from trf_core import read_trf,compute_sum
from smaart_runtime_paths_v868 import trace_directory

LAB=Path(r"D:\R59_SMAART8_TOP_RIGHT_DOCK_QA\R60_NATIVE_SMAART8_READONLY.png")
MAG=(215,368,920,257)
WIN=(0,0,1366,720)

def test_r60_dark_olive_pixels_are_green_not_grid():
    ar=np.zeros((220,600,3),dtype=np.uint8)
    ar[:]=[10,10,10]
    ar[40,:]=[36,36,36]  # Smaart neutral grid
    ar[100,40:290]=[64,94,64] # native dark green line
    ar[120,40:290]=[50,72,50] # antialiased native green
    mask=trace_color_mask(Image.fromarray(ar),"green")
    assert np.count_nonzero(mask)>=440
    assert not np.any(mask[40,40:290])
    assert not mask[150,100]

def test_r60_dark_green_trace_real_native_axis_verified():
    if not LAB.exists():pytest.skip("Live native Smaart8 QA fixture unavailable")
    folder=trace_directory(8)
    if folder is None:pytest.skip("Smaart8 traces unavailable")
    files=[folder/n for n in ("full 30 bien.trf","SUB SKY 2.trf")]
    if not all(p.exists() for p in files):pytest.skip("Exact original Smaart8 TRFs unavailable")
    im=Image.open(LAB)
    frame=NativeMagFrame(im,MAG,WIN)
    assert np.count_nonzero(frame._mask("green"))>=250
    traces=[read_trf(p) for p in files]
    fitted=_smaart8_native_source_axis(im,MAG,WIN,traces)
    assert fitted.accepted and fitted.color=="green" and fitted.source_index==0
    assert fitted.score>.90
    assert fitted.x_min==20 and fitted.x_max==20000
    assert -30<fitted.y_min<-10 and 10<fitted.y_max<30
    # Same screenshot, wrong source should not pass as a green trusted trace.
    mismatch=_smaart8_native_source_axis(im,MAG,WIN,[traces[1],traces[1]])
    assert not mismatch.accepted

def test_r60_sum_graphs_paint_using_verified_native_axis(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QImage,QPainter
    from PyQt6.QtCore import Qt
    from remix_duo.core.traces import synthetic
    from overlay_v7 import SumGraph
    app=QApplication.instance() or QApplication([])
    freq=np.geomspace(20.,20000.,450)
    a=synthetic("full 30 bien",freq,db=-9.,delay_ms=0.)
    b=synthetic("SUB SKY 2",freq,db=-11.,delay_ms=9.9)
    model=compute_sum(a,b,delay_ms=9.9)
    for kind in ("phase","mag"):
        g=SumGraph(kind)
        g.resize(920,257)
        g.f_min,g.f_max=20.,20000.
        g.require_native_x_axis=True
        g.native_x_axis_ready=True
        g.native_axis_ready=True
        g.y_min,g.y_max=(-180.,180.) if kind=="phase" else (-19.,20.)
        g.roi_guides=False
        g.set_data(model)
        out=QImage(920,257,QImage.Format.Format_ARGB32_Premultiplied)
        out.fill(Qt.GlobalColor.transparent)
        painter=QPainter(out)
        g.render(painter)
        painter.end()
        assert g._last_points>120,kind
        g.close()
