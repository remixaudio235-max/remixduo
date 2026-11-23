"""V8.56 visual-only unified Auto Phase / EQ / FIR layout checks.

All tests run Qt offscreen and never open Smaart, audio I/O, DSP or Sweep.
"""
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel
from test_v845_fir_one_trace import init


@pytest.fixture()
def ui():
    app,obs,engine,hub,_=init()
    try:
        hub.dock.apply_rect((580,140,205,560))
        hub.dock.show()
        app.processEvents()
        yield app,engine,hub
    finally:
        hub.close()
        engine.close()
        app.processEvents()


@pytest.mark.parametrize("mode,accent",[
    ("phase","#7DFF7E"),("eq","#FFA647"),("fir","#65DAFF")
])
def test_visual_modes_share_shell_but_keep_unique_colors(ui,mode,accent):
    app,engine,hub=ui
    hub.select(mode)
    app.processEvents()
    assert hub.dock._ux_v856
    assert hub.dock.heading.text().startswith(
        {"phase":"AUTO PHASE","eq":"AUTO EQ","fir":"AUTO FIR"}[mode])
    assert accent in hub.dock.heading.styleSheet()
    assert hub.dock.stack.currentWidget() is hub.pages[mode]
    assert hub.dock.width()==205
    assert hub.dock.scroll.horizontalScrollBarPolicy() == (
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    assert hub.dock.scroll.horizontalScrollBar().maximum()==0
    assert hub.dock.heading.toolTip()


@pytest.mark.parametrize("mode",["eq","fir"])
def test_primary_actions_above_results_visible_on_first_panel(ui,mode):
    app,engine,hub=ui
    hub.select(mode);app.processEvents()
    panel=hub.pages[mode]
    assert panel.main.indexOf(panel._action_row)<panel.main.indexOf(panel.summary)
    assert panel.calculate.isVisible()
    button_bottom=panel.calculate.mapTo(hub.dock.scroll.viewport(),panel.calculate.rect().bottomRight())
    assert button_bottom.y()<hub.dock.scroll.viewport().height()
    assert panel.main.indexOf(panel.source)>=0
    assert panel.main.indexOf(panel.details)>=0
    assert panel.main.indexOf(panel.summary)>=0
    assert not panel.main.itemAt(0).widget().isVisible()
    assert len(panel._ux_sections)==(2 if mode=='eq' else 3)
    assert all(x.objectName()=="uxSection" for x in panel._ux_sections)
    assert panel.details.isReadOnly()
    assert "ghi DSP" in panel.note.text()
    assert panel.source.currentData()==0


def test_eq_live_controls_preserved_with_compact_gain_row(ui):
    app,engine,hub=ui
    hub.select("eq");app.processEvents()
    eq=hub.eq
    assert eq.note.isHidden()
    assert eq._ux_gain_row.count()==2
    assert eq._ux_gain_boost_row.indexOf(eq.boost)>=0
    assert eq._ux_gain_cut_row.indexOf(eq.cut)>=0
    assert eq.main.indexOf(eq.lf)==-1 and eq.main.indexOf(eq.hf)==-1
    assert eq.main.indexOf(eq.roi_status)>=0
    assert eq.filter_count.value()==0
    assert eq.filter_count.specialValueText()=="AUTO"
    assert eq.boost.value()==0 and eq.cut.value()==-12
    assert eq.boost.isEnabled() and eq.cut.isEnabled()
    assert eq.lf.value()==60 and eq.hf.value()==8000
    assert eq.calculate.receivers(eq.calculate.clicked)>=1
    assert eq.export.receivers(eq.export.clicked)>=1
    assert eq.mageq_toggle.isChecked()
    assert eq.boost.specialValueText()=="AUTO"
    assert eq.cut.specialValueText()=="AUTO"


def test_fir_preserves_taps_and_export_callbacks(ui):
    app,engine,hub=ui
    hub.select("fir");app.processEvents()
    fir=hub.fir
    assert fir.note.isHidden()
    assert fir.taps.currentData()==0 and fir.taps.currentText()=="AUTO taps"
    assert fir.calculate.receivers(fir.calculate.clicked)>=1
    assert fir.export_txt.receivers(fir.export_txt.clicked)>=1
    assert fir.export_wav.receivers(fir.export_wav.clicked)>=1
    assert not fir.export_txt.isEnabled() and not fir.export_wav.isEnabled()
    assert fir.main.indexOf(fir._taps_row)>=0
    assert fir._taps_row.indexOf(fir.taps_label)==0
    assert fir._taps_row.indexOf(fir.taps)==1
    assert fir.main.indexOf(fir.overlay_status)>=0


def test_phase_preserves_three_choices_and_selected_pair_controls(ui):
    app,engine,hub=ui
    hub.select("phase");app.processEvents()
    assert len(engine.candidates)==3
    assert len(engine.trace_name_labels)==2
    assert len(engine.trace_compact_result)==2
    assert engine.solve.receivers(engine.solve.clicked)>=1
    assert engine.solve.height()==26
    assert engine.trace_card.height()==138
    assert engine.candidate_card.height()==167
    assert engine.header.isHidden()
    assert engine.lf.value()==60
    assert engine.hf.value()==200


@pytest.mark.parametrize("height", [310,420,560])
def test_small_dock_height_scrolls_vertically_only(ui,height):
    app,engine,hub=ui
    for mode in ("phase","eq","fir"):
        hub.select(mode)
        hub.dock.apply_rect((580,140,205,height))
        hub.dock.show()
        app.processEvents()
        assert hub.dock.height()==height
        assert hub.dock.width()==205
        assert hub.dock.scroll.horizontalScrollBar().maximum()==0
        assert hub.dock.scroll.verticalScrollBar().maximum()>=0
        assert hub.dock.stack.currentWidget() is hub.pages[mode]
        assert hub.dock.heading.isVisible()
