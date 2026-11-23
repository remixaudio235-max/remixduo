"""V8.115: SUM display follows Smaart's live smoothing; one solid pen.

Live 2026-11-11: Smaart showed 1/6 Oct (UIA ComboBox '1/6 Oct' in each plot)
while SmaartConfig.xml still said 1/48 Oct (saved at 13:32), so SUM was
smoothed 8x finer than the traces and looked far rougher. The user also asked
for the SUM to be drawn bold for every coherence.
"""
import os,time
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import pytest
from PyQt6.QtWidgets import QApplication
from smaart_live_smooth_v8115 import parse_smoothing,classify

PHASE=(252,112,1442,394);MAG=(252,549,1442,394)


@pytest.mark.parametrize("name,value",[("1/6 Oct",1/6),("1/48 Oct",1/48),
    ("None",0.0),(" 1 / 3  oct ",1/3),("dB FS Peak",None),("6 Oct",None),("",None)])
def test_parse(name,value):
    assert parse_smoothing(name)==value


def test_classify_live_uia_layout():
    # exact rects seen on Smaart Suite 9, 2026-11-11
    els=[("1/6 Oct",(1611,485,1676,503)),("1/6 Oct",(1611,922,1676,940)),
         ("None",(1810,115,1910,135))]          # meter combo outside plots
    assert classify(els,PHASE,MAG)=={"phase":1/6,"mag":1/6}


def test_classify_ambiguous_plot_is_omitted():
    els=[("1/6 Oct",(1611,485,1676,503)),("1/3 Oct",(1500,480,1560,500)),
         ("1/12 Oct",(1611,922,1676,940))]
    assert classify(els,PHASE,MAG)=={"mag":1/12}


@pytest.fixture
def engine():
    import overlay_v7 as gui
    app=QApplication.instance() or QApplication([])
    e=gui.App(demo=True);e.timer.stop();e.drag_timer.stop()
    end=time.monotonic()+5
    while e.current_sum is None and time.monotonic()<end:
        app.processEvents();time.sleep(.02)
    yield e
    e.close();app.processEvents()


def test_live_smoothing_overrides_saved_and_recalcs(engine):
    engine.on_live_smoothing({"mag":1/6,"phase":1/6})
    assert abs(float(engine.mag_smooth.currentData())-1/6)<1e-9
    assert abs(float(engine.phase_smooth.currentData())-1/6)<1e-9
    before=engine._last_smooth_poll
    engine._refresh_saved_smoothing()           # lagging XML must not win
    assert engine._last_smooth_poll==before
    assert abs(float(engine.mag_smooth.currentData())-1/6)<1e-9


def test_unknown_live_value_keeps_current(engine):
    current=engine.mag_smooth.currentIndex()
    engine.on_live_smoothing({"mag":1/5})
    assert engine.mag_smooth.currentIndex()==current


def test_single_solid_pen_for_all_coherence():
    import overlay_v7 as gui
    src=open(gui.__file__,encoding="utf-8").read()
    assert gui.SUM_PEN_WIDTH==3.5
    assert '2.0 if quality=="low"' not in src and "setAlpha(128)" not in src
