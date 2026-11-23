"""V8.88 FIR LF/HF direct native plot drag — UI only, no generator or Smaart writes."""
import os
os.environ["QT_QPA_PLATFORM"]="offscreen"

import math
from types import SimpleNamespace

import pytest
from PyQt6.QtWidgets import QApplication

from fir_roi_v888 import clamp_fir_drag
from roi_markers_v73 import hz_to_x
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub

PHASE=(252,84,1442,412)
MAG=(252,539,1442,412)


def test_fir_drag_clamps_to_one_octave_and_valid_band():
    assert clamp_fir_drag("LF",500,30,600)==300
    assert clamp_fir_drag("HF",70,120,15000)==240
    assert clamp_fir_drag("LF",5,30,16000)==20
    assert clamp_fir_drag("HF",60000,30,16000)==20000
    for kind,value,lf,hf in (
        ("BAD",30,30,16000),
        ("LF",math.nan,30,16000),
        ("HF",80,300,150),
        ("LF",float("inf"),30,16000),
    ):
        with pytest.raises(ValueError):
            clamp_fir_drag(kind,value,lf,hf)


def make_hub():
    app=QApplication.instance() or QApplication([])
    engine=App(False)
    engine.timer.stop()
    engine.plot_layout=SimpleNamespace(phase=PHASE,mag=MAG)
    engine.overlay_positioned=True
    engine._apply_plot_layout()
    hub=ToolHub(engine)
    hub.timer.stop()
    hub.native_eq.timer.stop()
    hub.native_fir.timer.stop()
    # Drag parity tests start in MAG intentionally; production defaults PHA.
    hub.fir.fir_mag_button.click()
    hub.select("fir")
    app.processEvents()
    return app,engine,hub


def close_hub(app,engine,hub):
    hub.close()
    engine.managed_mode=False
    engine.close()
    app.processEvents()


def test_fir_drag_moves_native_markers_updates_sidebar_without_changing_phase():
    app,engine,hub=make_hub()
    try:
        fir=hub.fir
        original_phase=(engine.lf.value(),engine.hf.value())
        assert engine.graph_mag.fir_roi_active
        assert not engine.graph_phase.fir_roi_active
        assert engine.graph_mag.isVisible()
        assert engine.graph_mag.fir_source is None
        for kind in ("LF","HF"):
            assert engine.fir_roi_markers[kind].isVisible()
            assert engine.fir_roi_line_grips[kind].isVisible()
            assert engine.fir_roi_line_grips[kind].height()>350
        assert not any(m.isVisible() for m in engine.roi_markers.values())
        # Simulate the line grip's global-X callback on real Smaart plot rect.
        fir._approved=object()
        fir.export_wav.setEnabled(True)
        engine.on_fir_roi_drag("LF",hz_to_x(120,MAG[0],MAG[2]))
        assert abs(fir.fir_lf.value()-120)<=1
        assert engine.fir_roi_lf_hz==fir.fir_lf.value()
        assert engine.graph_mag.fir_lf_hz==fir.fir_lf.value()
        assert engine.fir_roi_markers["LF"].frequency==fir.fir_lf.value()
        assert fir._approved is None
        assert not fir.export_wav.isEnabled()
        assert (engine.lf.value(),engine.hf.value())==original_phase
        # HF cannot move through LF: FIR needs at least 1 octave.
        engine.on_fir_roi_drag("HF",hz_to_x(55,MAG[0],MAG[2]))
        assert fir.fir_hf.value()>=2*fir.fir_lf.value()
        assert engine.fir_roi_hf_hz==fir.fir_hf.value()
    finally:
        close_hub(app,engine,hub)


def test_fir_mode_switch_reanchors_phase_plot_and_hides_on_other_tabs():
    app,engine,hub=make_hub()
    try:
        fir=hub.fir
        marker=engine.fir_roi_markers["LF"]
        assert marker.y()==MAG[1]+5
        fir.fir_mode.setCurrentIndex(1)
        app.processEvents()
        assert engine.fir_roi_mode=="phase"
        assert engine.graph_phase.fir_roi_active
        assert engine.graph_phase.isVisible()
        assert not engine.graph_mag.fir_roi_active
        assert not engine.graph_mag.isVisible()
        assert marker.y()==PHASE[1]+5
        engine.on_fir_roi_drag("LF",hz_to_x(200,PHASE[0],PHASE[2]))
        assert abs(fir.fir_lf.value()-200)<=1
        # Native host moves: reanchor both marker and touch strip.
        engine.plot_layout=SimpleNamespace(phase=(110,190,950,390),mag=MAG)
        engine._apply_plot_layout()
        assert marker.y()==195
        assert abs(engine.fir_roi_line_grips["LF"].x() -
                   (hz_to_x(fir.fir_lf.value(),110,950)-8))<=2
        hub.select("phase")
        app.processEvents()
        assert not any(x.isVisible() for x in engine.fir_roi_markers.values())
        assert not any(x.isVisible() for x in engine.fir_roi_line_grips.values())
        hub.select("fir")
        app.processEvents()
        assert all(x.isVisible() for x in engine.fir_roi_markers.values())
        hub.hide_workspace()
        app.processEvents()
        assert not engine.graph_phase.isVisible()
        assert not any(x.isVisible() for x in engine.fir_roi_line_grips.values())
    finally:
        close_hub(app,engine,hub)

def test_manual_spin_edits_keep_fir_guides_within_one_octave():
    app,engine,hub=make_hub()
    try:
        fir=hub.fir
        fir.fir_lf.setValue(17000)
        assert fir.fir_lf.value()==1250  # current HF is 2500
        fir.fir_hf.setValue(100)
        assert fir.fir_hf.value()==2500  # cannot cross the current LF
        assert engine.fir_roi_lf_hz==1250
        assert engine.fir_roi_hf_hz==2500
        assert engine.graph_mag.fir_roi_active
    finally:
        close_hub(app,engine,hub)
