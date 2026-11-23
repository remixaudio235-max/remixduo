"""V8.113: tick 'flicker' + silent Auto Phase failure seen live 2026-11-11.

1. printwindow_image computed std() over the FULL 1920x1032x3 image as float64
   (~45 MB per 0.16 s poll). Under low commit memory this raised MemoryError,
   the scan turned transient and the tick lock re-armed ("chập chờn").
   The blank check must work on a sparse sample.
2. A TRF that fails to load reported only to the hidden status label, so the
   user saw a verified pair but no SUM/Top 3 and no reason.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from concurrent.futures import Future
import numpy as np
from PIL import Image
import pytest
from PyQt6.QtWidgets import QApplication
import full_scan_v7 as scanner


def test_blank_check_uses_sparse_sample(monkeypatch):
    seen=[]
    real=np.asarray
    def spy(a,*k,**kw):
        out=real(a,*k,**kw); seen.append(out.size); return out
    monkeypatch.setattr(scanner.np,"asarray",spy)
    img=Image.fromarray((np.random.default_rng(1).random((1032,1920,3))*255).astype("uint8"))
    assert not scanner._image_looks_blank(img)
    assert max(seen)<=1032*1920*3//40, "full-frame array allocated for blank check"
    assert scanner._image_looks_blank(Image.new("RGB",(1920,1032),(20,20,20)))


def test_trace_load_failure_is_visible(monkeypatch):
    import overlay_v7 as gui
    import signal_tools_gui_v813 as tools
    app=QApplication.instance() or QApplication([])
    notices=[]
    monkeypatch.setattr(tools,"show_notice",lambda w,msg:notices.append(msg))
    e=gui.App(demo=True);e.timer.stop();e.drag_timer.stop()
    try:
        monkeypatch.setattr(e.controller,"is_current",lambda g,p:True,raising=False)
        fut=Future();fut.set_exception(ValueError("bad TRF samples"))
        e.loaded(1,("c:/sup bien 2-1.trf","c:/b.trf"),fut,None)
        assert e.current_traces is None
        assert not e.selection_warning.isHidden()
        assert "sup bien 2-1" in e.selection_warning.text()+e.selection_warning.toolTip()
        assert notices and "bad TRF samples" in notices[-1]
    finally:
        e.close();app.processEvents()
