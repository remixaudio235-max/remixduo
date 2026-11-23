"""V8.58: switching EQ/FIR -> Auto Phase must not collapse the workspace.

The selection gate controls available content/actions, not outer dock
geometry. Tests exercise the actual Qt stack with synthetic source only.
"""
import pytest
from PyQt6.QtWidgets import QApplication
from test_v845_fir_one_trace import init


@pytest.fixture
def session():
    app,observer,engine,hub,_=init()
    try:
        hub.dock.show()
        app.processEvents()
        yield app,engine,hub
    finally:
        hub.close()
        engine.close()
        app.processEvents()


@pytest.mark.parametrize("quality,verified",[
    ("invalid",False),("transient",False),
    ("weak",False),("valid",True),
])
@pytest.mark.parametrize("origin",["eq","fir"])
def test_tab_change_never_shrinks_dock_from_selection(session,origin,quality,verified):
    app,engine,hub=session
    rect=(555,390,205,410)
    hub.select(origin)
    hub.dock.apply_rect(rect)
    app.processEvents()
    assert hub.dock.height()==rect[3]
    engine._selection_quality=quality
    engine._selection_verified=verified
    hub.select("phase")
    hub.dock.apply_rect(rect)
    app.processEvents()
    assert hub.dock.stack.currentWidget() is engine
    assert hub.dock.height()==rect[3], (
        origin,quality,verified,hub.dock.height())
    assert hub.dock.scroll.horizontalScrollBar().maximum()==0
    assert hub.dock.stack.height()==hub.dock.page_heights["phase"]


def test_invalid_phase_keeps_action_safety_without_resizing_shell(session):
    app,engine,hub=session
    rect=(555,390,205,475)
    hub.select("eq")
    engine._selection_quality="invalid"
    engine._set_tick_presentation(False)
    hub.select("phase")
    for _ in range(6):
        hub.dock.apply_rect(rect)
        app.processEvents()
        assert hub.dock.height()==rect[3]
        assert not engine.solve.isEnabled()
        assert not engine.candidate_card.isVisible()
    # A later valid pair may show Top-3 again without HIDE.
    engine._selection_quality="valid"
    engine._set_tick_presentation(True)
    hub.dock.apply_rect(rect)
    app.processEvents()
    assert hub.dock.height()==rect[3]
    assert engine.trace_card.height()==138
    assert engine.candidate_card.isVisible()


def test_repeat_eq_phase_fir_and_small_window_no_hide_needed(session):
    app,engine,hub=session
    for height in (560,390,310):
        rect=(555,390,205,height)
        for i in range(12):
            mode=("eq","phase","fir","phase")[i%4]
            engine._selection_quality="invalid" if i%2 else "transient"
            engine._selection_verified=False
            hub.select(mode)
            hub.dock.apply_rect(rect)
            app.processEvents()
            assert hub.dock.height()==height
            assert hub.dock.width()==205
            assert hub.dock.stack.currentWidget() is hub.pages[mode]
            assert hub.dock.scroll.horizontalScrollBar().maximum()==0
            assert hub.dock.heading.isVisible()
