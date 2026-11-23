"""V8.37: preserve Mag LF-HF overlay independently of native Y, and register
smoothed Smaart trace to one proven native color/source, never guess.
All tests use synthetic data; no Smaart or soundcard writes.
"""
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage

from overlay_v7 import SumGraph
from trf_core import synthetic,compute_sum
from mag_sum_native_v826 import axis_from_native_image
import mag_sum_native_v826 as module
from tf_display_smoothing import smooth_log_octaves
from roi_markers_v73 import hz_to_x
from PIL import Image


def _image(graph):
    q=graph.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    bits=q.bits()
    bits.setsize(q.sizeInBytes())
    return np.frombuffer(bits,dtype=np.uint8).copy().reshape(q.height(),q.width(),4)


def test_mag_crossover_highlight_survives_unverified_native_y():
    app=QApplication.instance() or QApplication([])
    hz=np.geomspace(20.,20000.,1024)
    data=compute_sum(synthetic("A",hz),synthetic("B",hz))
    g=SumGraph("mag")
    g.resize(1000,360)
    g.set_data(data)
    g.require_native_axis=True
    g.native_axis_ready=False
    g.lf_hz=114.
    g.hf_hz=392.
    g.show()
    app.processEvents()
    try:
        g.roi_guides=False
        base=_image(g)
        g.roi_guides=True
        g.update()
        app.processEvents()
        colored=_image(g)
        lf=int(hz_to_x(g.lf_hz,0,1000,20.,20000.))
        hf=int(hz_to_x(g.hf_hz,0,1000,20.,20000.))
        delta=np.abs(colored.astype(np.int16)-base.astype(np.int16)).sum(axis=2)
        assert np.count_nonzero(delta[38:320,lf+12:hf-12]>7)>12000
        assert np.count_nonzero(delta[38:320,5:lf-20]>7)<30
        assert g._cache_rebuilds==0, "Never draw unverified SUM magnitude"
        assert not g.native_axis_ready
    finally:
        g.close()


def test_sum_mag_requires_one_distinct_source_with_correct_smoothing(monkeypatch):
    frequencies=np.geomspace(20.,20000.,240)
    source0=synthetic("boh",frequencies)
    source1=synthetic("sub",frequencies,db=-12.,delay_ms=4.5)
    traces=(source0,source1)
    expected=smooth_log_octaves(frequencies,
         20*np.log10(np.maximum(np.abs(source0.h),1e-15)),1/6)
    seen=[]
    def mask(image,color):
        return np.ones((16,16),dtype=bool) if color in ("magenta","gold") else np.zeros((16,16),bool)
    def fit(image,plot,window,f,db,coherence,*,trace_color,frame=None):
        good=(trace_color=="magenta" and np.allclose(db,expected,atol=1e-9))
        seen.append((trace_color,good))
        return SimpleNamespace(accepted=good,score=1.0 if good else 0.,
            alternative_score=0.,center_px=185.,px_per_db=10.,
            source_median_db=3.,bins=200)
    monkeypatch.setattr(module.NativeMagFrame,"visible_colors",
                        lambda self,colors:tuple(c for c in colors
                                                 if c in ("magenta","gold")))
    monkeypatch.setattr(module,"fit_native_mag",fit)
    frame=axis_from_native_image(Image.new("RGB",(1920,1040)),
            (252,539,1442,412),(0,0,1920,1040),traces)
    assert frame.accepted and frame.color=="magenta" and frame.source_index==0
    assert abs(frame.y_max-frame.y_min-41.2)<.001
    assert "smoothing=0.166667" in frame.reason
    assert any(g for _,g in seen)


def test_sum_mag_rejects_two_equally_matched_sources(monkeypatch):
    traces=tuple(synthetic(n,np.geomspace(20.,20000.,240))
                 for n in ("A","B"))
    monkeypatch.setattr(module.NativeMagFrame,"visible_colors",
                        lambda self,colors:("magenta",))
    def fit(*args,**kwargs):
        return SimpleNamespace(accepted=True,score=1.,alternative_score=0.,
            center_px=185.,px_per_db=10.,source_median_db=3.,bins=200)
    monkeypatch.setattr(module,"fit_native_mag",fit)
    result=axis_from_native_image(Image.new("RGB",(1920,1040)),
        (252,539,1442,412),(0,0,1920,1040),traces)
    assert not result.accepted
    assert result.reason=="Ambiguous native trace identity"
