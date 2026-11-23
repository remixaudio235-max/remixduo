"""V8.43: EQ-number-only markers, one hover tooltip, Smaart click-through."""
from types import SimpleNamespace
import time

import numpy as np
from PyQt6.QtCore import QPoint,Qt
from PyQt6.QtWidgets import QApplication

import overlay_v7 as overlay
from overlay_v7 import SumGraph
from mageq_visual_v13 import marker_hover_at,PEQMarker
from native_eq_mag_v06 import build_state,FitFrame
from smaart_native_mag_fit import NativeMagFit

PLOT=(252,539,1442,412)


def make_source():
    freq=np.geomspace(20.,20000.,1800)
    h=np.full(len(freq),10**(-9/20),dtype=complex)
    coh=np.ones_like(freq)
    bands=[SimpleNamespace(freq_hz=hz,gain_db=g,q=q)
           for hz,g,q in [(70,3.0,1.3),(125,-2.5,2.0),
                          (420,1.1,3.2),(1440,-4.2,1.8)]]
    return build_state(freq,h,coh,tuple(bands),fs=48000,
                       source_index=0,source_name="QA",revision=43)


def test_nearest_hit_only_and_no_far_hit():
    markers=(
        PEQMarker(1,100.,2.,2.,100.,150.,True,True),
        PEQMarker(2,107.,-2.,2.,108.,150.,True,True),
        PEQMarker(3,300.,4.,2.,400.,150.,False,True))
    assert marker_hover_at(markers,101,151)==1
    assert marker_hover_at(markers,107,150)==2
    assert marker_hover_at(markers,250,150) is None
    assert marker_hover_at(markers,400,150) is None


def test_mageq_default_zero_details_hover_one_and_clear(monkeypatch):
    app=QApplication.instance() or QApplication([])
    src=make_source()
    fit=NativeMagFit(171.,11.5,0.,1.,0.,0,True,"0 dB GRID")
    frame=FitFrame(src.revision,PLOT,fit,"GRID",time.monotonic())
    graph=SumGraph("mag")
    graph.setGeometry(*PLOT)
    graph.eq_roi_active=True
    graph.set_mageq(src,frame)
    graph.show()
    app.processEvents()
    try:
        assert graph.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        assert bool(graph.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        assert graph.mageq_annotation_stats["markers"]==4
        assert graph.mageq_annotation_stats["labels"]==0
        assert graph._hover_number is None
        assert graph._hover_timer.isActive()
        visible=[p for p in graph._hover_markers if p.visible]
        assert visible
        target=visible[0]
        near=graph.mapToGlobal(QPoint(round(target.x),round(target.y)))
        monkeypatch.setattr(overlay,"QCursor",SimpleNamespace(pos=lambda:near))
        graph._poll_mageq_hover()
        app.processEvents()
        assert graph._hover_number==target.number
        assert graph.mageq_annotation_stats["labels"]==1
        count=graph.mageq_draw_count
        graph._poll_mageq_hover()
        app.processEvents()
        assert graph.mageq_draw_count==count, "No frame rebuild on stationary cursor"
        away=graph.mapToGlobal(QPoint(graph.width()-8,graph.height()-8))
        monkeypatch.setattr(overlay,"QCursor",SimpleNamespace(pos=lambda:away))
        graph._poll_mageq_hover()
        app.processEvents()
        assert graph._hover_number is None
        assert graph.mageq_annotation_stats["labels"]==0
        # Old EQ selection must NEVER retain a popup after changing source.
        graph.set_mageq()
        app.processEvents()
        assert not graph._hover_timer.isActive()
        assert graph._hover_markers==()
    finally:
        graph.close()


def test_hidden_or_other_tool_never_shows_details(monkeypatch):
    app=QApplication.instance() or QApplication([])
    src=make_source()
    fit=NativeMagFit(171.,11.5,0.,1.,0.,0,True,"0 dB GRID")
    frame=FitFrame(src.revision,PLOT,fit,"GRID",time.monotonic())
    graph=SumGraph("mag")
    graph.setGeometry(*PLOT)
    graph.eq_roi_active=True
    graph.set_mageq(src,frame)
    graph.show()
    app.processEvents()
    try:
        marker=next(x for x in graph._hover_markers if x.visible)
        pos=graph.mapToGlobal(QPoint(round(marker.x),round(marker.y)))
        monkeypatch.setattr(overlay,"QCursor",SimpleNamespace(pos=lambda:pos))
        graph._poll_mageq_hover()
        app.processEvents()
        assert graph._hover_number==marker.number
        graph.eq_roi_active=False
        graph._poll_mageq_hover()
        app.processEvents()
        assert graph._hover_number is None
    finally:
        graph.close()
