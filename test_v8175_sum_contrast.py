"""V8.175 offscreen SUM paint contrast test across Smaart UI themes."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage,QPainter
from PyQt6.QtCore import Qt
from remix_duo.core.traces import synthetic,compute_sum
from overlay_v7 import SumGraph

def test_sum_magnitude_raster_recolors_light_vs_dark_and_remains_visible():
    app=QApplication.instance() or QApplication([])
    frequencies=np.geomspace(20.,20000.,420)
    a=synthetic("LF",frequencies,db=-9,delay_ms=0.)
    b=synthetic("HF",frequencies,db=-6,delay_ms=.9)
    model=compute_sum(a,b,delay_ms=0.2)
    graph=SumGraph("mag")
    graph.resize(900,300)
    graph.y_min,graph.y_max=-24.,24.
    graph.roi_guides=False
    graph.require_native_axis=True
    graph.native_axis_ready=True
    graph.set_data(model)
    images={}
    for theme in ("dark","light"):
        graph.theme=theme
        graph._paint_cache=None
        shot=QImage(900,300,QImage.Format.Format_ARGB32_Premultiplied)
        shot.fill(Qt.GlobalColor.transparent)
        painter=QPainter(shot)
        graph.render(painter)
        painter.end()
        assert graph._last_points>100
        assert graph._paint_cache["key"][-1]==theme
        # Inspect original cached line color, not composited canvas color.
        colors=np.array([3,8,12])
        line=graph._paint_cache["trace_bitmap"].toImage()
        sample_count=0
        for y in range(0,line.height(),3):
            for x in range(0,line.width(),3):
                q=line.pixelColor(x,y)
                if theme=="light":
                    sample_count+=int(q.green()>60 and q.red()<45 and q.blue()<90 and q.alpha()>180)
                else:
                    sample_count+=int(q.green()>180 and q.red()<140 and q.blue()<100 and q.alpha()>180)
        assert sample_count>5,(theme,sample_count)
        images[theme]=sample_count
    assert images["dark"]>0 and images["light"]>0
    graph.close()
