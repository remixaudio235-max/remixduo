"""V8.35 crossover highlight: both plots, ROI motion, cached raster parity."""
import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication
from overlay_v7 import SumGraph
from trf_core import synthetic,compute_sum
from roi_markers_v73 import hz_to_x
from PyQt6.QtGui import QImage
from pathlib import Path

@pytest.mark.parametrize("kind",["phase","mag"])
def test_visible_roi_highlight_follows_both_markers_without_raster_rebuild(kind):
    app=QApplication.instance() or QApplication([])
    freq=np.geomspace(20.,20000.,2048)
    sum_tf=compute_sum(synthetic("A",freq,delay_ms=4.0),
                       synthetic("B",freq,delay_ms=4.3))
    graph=SumGraph(kind)
    graph.resize(1000,360)
    graph.require_native_axis=False
    graph.set_data(sum_tf)
    graph.show()
    app.processEvents()
    try:
        def grab(enabled,lf,hf):
            graph.roi_guides=enabled
            graph.lf_hz=lf
            graph.hf_hz=hf
            graph.update()
            app.processEvents()
            im=graph.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
            bits=im.bits()
            bits.setsize(im.sizeInBytes())
            return np.frombuffer(bits,dtype=np.uint8).copy().reshape(im.height(),im.width(),4)
        no_roi=grab(False,60,200)
        initial_rebuilds=graph._cache_rebuilds
        colored=grab(True,60,200)
        assert graph._cache_rebuilds==initial_rebuilds
        xlf=round(hz_to_x(60,0,1000,20,20000))
        xhf=round(hz_to_x(200,0,1000,20,20000))
        # Interior cyan tint is broad/visible and outside plot stays unchanged.
        delta=np.abs(colored.astype(np.int16)-no_roi.astype(np.int16)).sum(axis=2)
        assert np.count_nonzero(delta[35:315,xlf+12:xhf-12]>9)>10000
        assert np.count_nonzero(delta[35:315,4:xlf-20]>9)<30
        assert np.count_nonzero(delta[35:315,xhf+20:950]>9)<30
        moved=grab(True,90,450)
        assert graph._cache_rebuilds==initial_rebuilds
        old_strip=np.abs(moved.astype(np.int16)-no_roi.astype(np.int16)).sum(axis=2)
        new_lf=round(hz_to_x(90,0,1000,20,20000))
        new_hf=round(hz_to_x(450,0,1000,20,20000))
        assert np.count_nonzero(old_strip[45:310,new_lf+10:new_hf-15]>9)>7000
        if kind=="mag":
            assert graph.grab().save(str(Path(__file__).with_name('V835_HIGHLIGHT_MAG_QA.png')))
        else:
            assert graph.grab().save(str(Path(__file__).with_name('V835_HIGHLIGHT_PHASE_QA.png')))
        # Disabling crossover must remove the tint but not alter H(f).
        cleared=grab(False,90,450)
        assert np.array_equal(cleared,no_roi)
        assert graph.data is sum_tf
    finally:
        graph.hide()
        graph.close()
