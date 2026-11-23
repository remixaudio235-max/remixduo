"""V8.33: compact invalid trace count, unchanged verified trace/Top3."""
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub


def test_three_trace_warning_compacts_without_replacing_trace_logic():
    app=QApplication.instance() or QApplication([])
    engine=App(demo=False)
    engine.timer.stop()
    hub=ToolHub(engine)
    hub.timer.stop()
    hub.native_eq.timer.stop()
    try:
        engine._selection_quality='invalid'
        engine._set_tick_presentation(False)
        engine.selection_warning.setText('Đang bật 3 Trace — cần đúng 2')
        engine.selection_warning.show()
        hub.select('phase')
        hub.dock.apply_rect((1420,400,205,310))
        hub.dock.show()
        app.processEvents()
        # V8.122: a 310 px dock (< 424) uses the compact Auto Phase page.
        assert engine._compact_layout
        assert engine.trace_card.height()==engine.COMPACT_TRACE_H[1]
        assert engine.selection_warning.height()==36
        assert engine.selection_warning.isVisible()
        assert engine.trace_card.y()<110
        # V8.58: only the warning card is compact; the outer workspace
        # must keep Smaart's 310px allocation for instant tab switching.
        assert hub.dock.height()==310
        assert not engine.candidate_card.isVisible()
        assert engine.solve.height()==26
        assert hub.dock.grab().save(str(Path(__file__).with_name('V833_INVALID_COMPACT_QA.png')))

        # Normal valid 2-trace state keeps exactly two rows and all Top3.
        engine._selection_quality='verified'
        engine._set_tick_presentation(True)
        engine.selection_warning.hide()
        hub.dock.apply_rect((1420,400,205,310))
        app.processEvents()
        assert engine.trace_card.height()==engine.COMPACT_TRACE_H[0]
        assert hub.dock.height()==310
        assert engine.candidate_card.isVisible()
        assert engine.candidate_card.height()==engine.COMPACT_CANDIDATE_H
        assert all(w.isVisible() for w in engine.trace_name_labels)
        assert all(w.isVisible() for w in engine.trace_compact_result)
        assert len(engine.candidates)==3
        assert hub.dock.grab().save(str(Path(__file__).with_name('V833_VERIFIED_LAYOUT_QA.png')))

        # Pending snapshots must not randomly shrink dock while verifying.
        engine._selection_quality='pending'
        engine._set_tick_presentation(False)
        engine.selection_warning.setText('Xác minh tick 2/3')
        engine.selection_warning.show()
        hub.dock.apply_rect((1420,400,205,310))
        app.processEvents()
        assert engine.trace_card.height()==engine.COMPACT_TRACE_H[1]
        assert hub.dock.height()==310
        assert engine.selection_warning.height()==36
    finally:
        hub.timer.stop()
        engine.timer.stop()
        hub.dock.hide()
        hub.hide()
        engine.hide()
