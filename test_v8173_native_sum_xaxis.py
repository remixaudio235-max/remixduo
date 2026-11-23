"""V8.173: dynamic logarithmic frequency alignment for Smaart8 TF overlays."""
import os,math
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import pytest
from PyQt6.QtWidgets import QApplication
from roi_markers_v73 import hz_to_x,x_to_hz,ROILineGrip
from overlay_v7 import SumGraph

def test_smaart8_native_10_10k_and_marker():
    app=QApplication.instance() or QApplication([])
    width=1262
    axis=(10.,10000.)
    x=hz_to_x(60.,185,width,*axis)
    y=hz_to_x(200.,185,width,*axis)
    assert 510 < x < 530
    assert 725 < y < 745
    assert abs(x_to_hz(x,185,width,*axis)-60)<1e-6
    old=hz_to_x(60.,185,width)
    assert x-old>110, "Old axis silently displays ROI at wrong native frequency"
    grip=ROILineGrip("LF",lambda *a:None)
    grip.set_line_geometry((185,80,width,400),60.,label_margin=0,
                           fmin=axis[0],fmax=axis[1])
    assert abs(grip.x()+grip.WIDTH//2-x)<=1
    grip.close()
    graph=SumGraph("phase")
    graph.f_min,graph.f_max=axis
    graph.native_x_axis_ready=True
    assert graph.f_min==10 and graph.f_max==10000
    graph.close()
