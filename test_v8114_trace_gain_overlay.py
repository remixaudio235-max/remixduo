"""V8.114/V8.115 overlay: Smaart trace dB offset moves SUM (auto-measured only).

V8.115: user asked to remove the per-trace dB boxes and "A" buttons (too
cluttered); the offset is measured from Smaart pixels in the background.
"""
import os,time
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from types import SimpleNamespace as NS
import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication,QDoubleSpinBox
from trace_offset_native_v8114 import TraceOffset


@pytest.fixture
def engine():
    import overlay_v7 as gui
    app=QApplication.instance() or QApplication([])
    e=gui.App(demo=True);e.timer.stop();e.drag_timer.stop()
    end=time.monotonic()+5
    while e.current_sum is None and time.monotonic()<end:
        app.processEvents();time.sleep(.02)
    assert e.current_sum is not None
    yield e
    e.close();app.processEvents()


def test_no_gain_widgets_in_panel(engine):
    assert not hasattr(engine,"trace_gain_spins")
    assert not hasattr(engine,"trace_gain_auto_buttons")
    spins=[w for w in engine.trace_card.findChildren(QDoubleSpinBox)]
    assert spins==[]


def test_gain_moves_sum_and_invalidates_top3(engine):
    before=np.nanmedian(engine.current_sum.mag_db)
    engine.last_solve=["stale"]
    engine.set_trace_gain(0,7.0)
    after=np.nanmedian(engine.current_sum.mag_db)
    assert after-before>2.0, (before,after)
    assert engine.last_solve is None
    engine.set_trace_gain(0,-2.0)
    assert np.nanmedian(engine.current_sum.mag_db)<after


def _key(e):
    return (e.plot_hwnd,tuple(e.plot_layout.mag),tuple(e.current_pair or ()),
            round(float(e.graph_mag.y_min),3),round(float(e.graph_mag.y_max),3))


def test_auto_offsets_fresh_key_only_and_hold_on_failure(engine):
    engine.plot_hwnd=77;engine.plot_layout=NS(mag=(1,2,3,4),phase=(0,0,1,1))
    res=[TraceOffset(7.0,"red","đo"),TraceOffset(-4.0,"teal","đo")]
    engine.on_trace_offsets((_key(engine)[:1]+(9,9,9,9)+_key(engine)[2:],res))
    assert engine.trace_gain_db==[0.0,0.0]             # stale key ignored
    engine.on_trace_offsets((_key(engine),res))
    assert engine.trace_gain_db==[7.0,-4.0]
    engine.on_trace_offsets((_key(engine),[TraceOffset(None,None,"x")]*2))
    assert engine.trace_gain_db==[7.0,-4.0]            # failed measure keeps value


def test_offset_jitter_does_not_wipe_top3(engine):
    """V8.116: live measurement flips 3.9<->4.0 dB; Top 3 must survive."""
    engine.plot_hwnd=77;engine.plot_layout=NS(mag=(1,2,3,4),phase=(0,0,1,1))
    engine.on_trace_offsets((_key(engine),[TraceOffset(None,None,"x"),TraceOffset(4.0,"teal","đo")]))
    assert engine.trace_gain_db==[0.0,4.0]
    engine.last_solve=["kept"]
    for v in (3.9,4.0,3.9,4.1,3.8):
        engine.on_trace_offsets((_key(engine),[TraceOffset(None,None,"x"),TraceOffset(v,"teal","đo")]))
    assert engine.trace_gain_db==[0.0,4.0] and engine.last_solve==["kept"]
    engine.on_trace_offsets((_key(engine),[TraceOffset(None,None,"x"),TraceOffset(5.0,"teal","đo")]))
    assert engine.trace_gain_db==[0.0,5.0] and engine.last_solve is None


def test_new_pair_resets_gains(engine):
    engine.set_trace_gain(0,5.0)
    engine.on_selection(None)
    assert engine.trace_gain_db==[0.0,0.0]
