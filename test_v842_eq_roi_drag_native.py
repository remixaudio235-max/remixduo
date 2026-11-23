"""V8.42 regression: independent Auto EQ dashed LF/HF on Smaart native Mag.

No Smaart writes or hardware use. Offscreen Qt, read-only fixtures.
"""
import os
os.environ["QT_QPA_PLATFORM"]="offscreen"

from types import SimpleNamespace
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from roi_markers_v73 import hz_to_x
from overlay_v7 import App,SumGraph
from signal_tools_gui_v813 import ToolHub
from test_v16_independent_one_tick import setup,tick


PHASE=(252,84,1442,412)
MAG=(252,539,1442,412)


def _hub():
    app=QApplication.instance() or QApplication([])
    observer=setup()
    for _ in range(3):tick(observer,{0})
    engine=App(False)
    engine.timer.stop()
    engine.observer=observer
    engine.current_pair=None
    engine.current_traces=None
    engine._selection_verified=False
    engine.plot_layout=SimpleNamespace(phase=PHASE,mag=MAG)
    engine.overlay_positioned=True
    engine._apply_plot_layout()
    hub=ToolHub(engine)
    hub.timer.stop()
    hub.native_eq.timer.stop()
    hub.select("eq")
    app.processEvents()
    return app,engine,hub,observer


def test_eq_panel_replaces_two_input_boxes_with_native_drag_lines():
    app,engine,hub,_=_hub()
    try:
        eq=hub.eq
        assert eq.main.indexOf(eq.lf)==-1
        assert eq.main.indexOf(eq.hf)==-1
        assert not eq.lf.isVisible() and not eq.hf.isVisible()
        assert eq.main.indexOf(eq.roi_status)>=0
        assert eq.filter_count.prefix()=="Số PEQ tối đa "
        assert eq.filter_count.value()==0
        assert eq.filter_count.specialValueText()=="AUTO"
        assert eq._parameters()["lf"]==60.0
        assert eq._parameters()["hf"]==8000.0
        assert engine.graph_mag.eq_roi_active
        assert engine.graph_mag.isVisible()
        assert not engine.graph_phase.isVisible()
        for name in ("LF","HF"):
            marker=engine.eq_roi_markers[name]
            grip=engine.eq_roi_line_grips[name]
            assert marker.isVisible() and grip.isVisible()
            assert grip.geometry().height()>350
        assert not any(m.isVisible() for m in engine.roi_markers.values())
    finally:
        hub.close();engine.close();app.processEvents()


def test_drag_eq_lines_changes_only_eq_solver_roi_and_clears_old_peq():
    app,engine,hub,_=_hub()
    try:
        eq=hub.eq
        phase_range=(engine.lf.value(),engine.hf.value())
        eq.result=object()
        eq.export.setEnabled(True)
        engine.on_eq_roi_drag("LF",hz_to_x(125.0,MAG[0],MAG[2]))
        assert abs(eq.lf.value()-125.)<.1
        assert abs(engine.graph_mag.eq_lf_hz-125.)<.1
        assert "125 Hz" in eq.roi_status.text()
        assert eq.result is None and not eq.export.isEnabled()
        assert eq._parameters()["lf"]==125.0
        engine.on_eq_roi_drag("HF",hz_to_x(1700.,MAG[0],MAG[2]))
        assert abs(eq.hf.value()-1700.)<1.
        assert eq._parameters()["hf"]==1700.0
        assert (engine.lf.value(),engine.hf.value())==phase_range
        # Never allow HF to cross LF; limits are sourced from one range model.
        engine.on_eq_roi_drag("HF",hz_to_x(30.,MAG[0],MAG[2]))
        assert eq.hf.value()>eq.lf.value()
        engine.on_eq_roi_drag("LF",hz_to_x(19000.,MAG[0],MAG[2]))
        assert eq.lf.value()<eq.hf.value()
    finally:
        hub.close();engine.close();app.processEvents()


def test_eq_roi_is_visible_without_computed_mageq_and_hidden_in_phase_mode():
    app,engine,hub,_=_hub()
    try:
        graph=engine.graph_mag
        assert graph.mageq_source is None
        graph.set_data(None)
        assert graph.eq_roi_active
        image=graph.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        data=image.bits()
        data.setsize(image.sizeInBytes())
        rgb=np.frombuffer(data,dtype=np.uint8).reshape(image.height(),image.width(),4)
        left=int(round(hz_to_x(60.,0,graph.width())))
        right=int(round(hz_to_x(8000.,0,graph.width())))
        # Dashed line segments show at both LF/HF without solver data.
        assert np.count_nonzero(rgb[35:370,left,3]>170)>30
        assert np.count_nonzero(rgb[35:370,right,0]>170)>30
        hub.select("phase")
        app.processEvents()
        assert not graph.eq_roi_active
        assert not any(x.isVisible() for x in engine.eq_roi_markers.values())
        assert not any(x.isVisible() for x in engine.eq_roi_line_grips.values())
        hub.select("eq")
        assert graph.eq_roi_active
        hub.hide_workspace()
        app.processEvents()
        assert not graph.eq_roi_active
    finally:
        hub.close();engine.close();app.processEvents()
