"""V8.123: red frame on changed trace rows + trace name in Smaart colour.

User 2026-11-12: red frame around every trace whose delay / polarity is
changed (both traces -> both framed); trace names more prominent, in the
trace's own Smaart colour.

Real frames: Smaart 8 Data Bar fixture (3 ticked rows) and a Data Bar crop
of the user's Smaart Suite screenshot (sub p5-1 + find 1,2ms-1 ticked).
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from PIL import Image
from selection_v7 import icon_color
from full_scan_v7 import _page
from smaart8_databar_v8121 import v8_icon_color_rect,v8_row_states

FIX=Path(__file__).with_name("fixtures")


def test_icon_color_real_smaart8_rows():
    im=Image.open(FIX/"smaart8_databar_3on_1920x1032.png")
    colors=[icon_color(im,(20,y0,50,y1))
            for y0,y1,_ in v8_row_states(im,(0,0,1920,1032))]
    assert colors==["#00735F","#054691","#AF3778"]


def test_v8_color_roi_uses_window_dpi_not_1920_width():
    # At 150%, the native icon gutter is x=30..75 even on a 1920px host.
    # Scaling from host width would incorrectly keep x=20..50.
    assert v8_icon_color_rect(144,210,238,host_top=100)==(30,110,75,138)


def test_page_reports_suite_icon_colors_for_ticked_rows():
    im=Image.open(FIX/"smaart9_suite_databar_crop_200x430.png")
    colors={}
    states=_page(im,list(range(18)),0,24,0,430,17,22,colors=colors)
    assert [i for i,s in states.items() if s=="on"]==[5,6]
    assert colors[5]=="#726D04"      # sub p5-1: olive trace in the plot
    assert colors[6]=="#6677A8"      # find 1,2ms-1: slate-blue trace
    # Legacy callers (no dict) get exactly the same tick states.
    assert _page(im,list(range(18)),0,24,0,430,17,22)==states


def test_icon_color_never_invents_for_grey():
    assert icon_color(Image.new("RGB",(16,16),(120,120,120)),(0,0,16,16)) is None


class _Observer:
    order=[];states={}
    def __init__(self,colors):self.colors=colors
    def trace_color(self,name):return self.colors.get(name)


def _engine():
    from PyQt6.QtWidgets import QApplication
    from overlay_v7 import App
    app=QApplication.instance() or QApplication([])
    engine=App(False)
    engine.timer.stop()
    return app,engine


def test_red_frame_only_on_changed_trace_and_smaart_name_color():
    from PyQt6.QtGui import QColor
    app,engine=_engine()
    try:
        a,b=r"C:\s\sub p5-1.trf",r"C:\s\find 1,2ms-1.trf"
        engine.observer=_Observer({a:"#726D04",b:"#6677A8"})
        engine.current_pair=(a,b)
        engine._set_tick_presentation(True)
        engine.delay.setValue(0.0);engine.invert.setChecked(False)
        engine._update_delay_route_label()
        assert engine.trace_changed==[False,False]
        assert "#FF3B3B" not in engine.trace_change_frames[1].styleSheet()
        engine.delay.setValue(6.40)
        engine.invert.setChecked(True)
        engine._update_delay_route_label()
        assert engine.trace_changed==[False,True]     # REF trace untouched
        assert "#FF3B3B" in engine.trace_change_frames[1].styleSheet()
        assert "#FF3B3B" not in engine.trace_change_frames[0].styleSheet()
        # Polarity inversion alone also counts as a change.
        engine.delay.setValue(0.0)
        engine._update_delay_route_label()
        assert engine.trace_changed==[False,True]
        # Names in the trace's own hue, brightened for the dark panel.
        for i,src in enumerate(("#726D04","#6677A8")):
            css=engine.trace_name_labels[i].styleSheet()
            shown=QColor(css.split("color:")[1].split(";")[0])
            assert abs(shown.hsvHue()-QColor(src).hsvHue())<=3
            assert shown.valueF()>=.94
        engine.invert.setChecked(False)
        engine._update_delay_route_label()
        assert engine.trace_changed==[False,False]
    finally:
        engine.close();app.processEvents()


def test_frame_rule_is_per_row():
    """The solver delays only the non-REF trace today; the frame follows the
    row that actually changed, so two changed rows would show two frames."""
    app,engine=_engine()
    try:
        engine.current_pair=("x.trf","y.trf")
        engine._set_tick_presentation(True)
        engine.delay.setValue(1.2)
        engine._update_delay_route_label()
        assert engine.trace_changed==[False,True]
        engine.ref_choice.setCurrentIndex(1)
        engine.delay.setValue(1.2)
        engine._update_delay_route_label()
        assert engine.trace_changed==[True,False]
    finally:
        engine.close();app.processEvents()


def test_unknown_color_falls_back_to_white_and_frames_hide_when_invalid():
    app,engine=_engine()
    try:
        engine.observer=_Observer({})
        engine.current_pair=("x.trf","y.trf")
        engine._set_tick_presentation(True)
        engine._update_delay_route_label()
        assert "#F5FDFF" in engine.trace_name_labels[0].styleSheet()
        engine._set_tick_presentation(False)
        assert not any(f.isVisibleTo(engine) for f in engine.trace_change_frames)
    finally:
        engine.close();app.processEvents()
