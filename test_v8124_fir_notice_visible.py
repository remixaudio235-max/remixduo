"""V8.124: Auto FIR failure reason must be visible in a short dock.

User 2026-11-12: "Auto FIR không tạo FIR được". The FIR summary/details are
hidden (V8.98) so the only feedback is the toast, which was placed at the
bottom of the whole FIR page (~300-540 px) inside the scrolling dock. With
the V8.122 compact/overlap docks (200-400 px) the toast sat below the visible
area: clicking TẠO FIR seemed to do nothing.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PyQt6.QtCore import QRect


def _visible_in_dock(hub,label):
    viewport=hub.dock.scroll.viewport()
    top_left=label.mapTo(viewport,label.rect().topLeft())
    rect=QRect(top_left,label.size())
    return viewport.rect().contains(rect)


def test_fir_hold_notice_inside_short_dock_viewport():
    from test_v845_fir_one_trace import init
    app,observer,engine,hub,fir=init()
    try:
        hub.dock.apply_rect((1720,545,195,256))     # real Smaart 8 3-engine dock
        hub.dock.show()
        hub.select("fir")
        app.processEvents()
        assert fir.height()>hub.dock.height()        # page really scrolls
        fir.warning("FIR Phase HOLD: Excess Phase tệ hơn (60.0° → 66.1°)")
        app.processEvents()
        anchor=(engine.graph_phase if engine.graph_phase.isVisible()
                else engine.graph_mag)
        label=anchor._remix_notice
        assert label.isVisible()
        assert label.isWindow()
        assert not _visible_in_dock(hub,label)
        # Scrolled to the bottom: the notice follows the visible area.
        bar=hub.dock.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
        app.processEvents()
        fir.warning("FIR cần đúng 1 Trace tick đã xác minh trong Smaart")
        app.processEvents()
        assert label.isVisible() and label.isWindow()
    finally:
        hub.close();app.processEvents()


def test_saved_mag_smoothing_1_48_is_verified(tmp_path):
    """Live 2026-11-12: Magnitude "1/48 Oct" with saved smoothingId=2 made
    native_fir_frame return None on every frame (no FIR curve ever drawn)."""
    from smaart_smooth_sync_v811 import read_saved_smooth
    cfg=tmp_path/"SmaartConfig.xml"
    cfg.write_text(
        "<root>"
        "<plotProperties><name>Phase1</name><visible>1</visible>"
        "<smoothingId>5</smoothingId></plotProperties>"
        "<plotProperties><name>Magnitude1</name><visible>1</visible>"
        "<smoothingId>2</smoothingId></plotProperties>"
        "</root>",encoding="utf-8")
    snap=read_saved_smooth(cfg)
    assert snap is not None
    assert snap.mag_oct==1/48 and snap.mag_verified
    assert snap.phase_oct==1/6 and snap.phase_verified


def test_fir_hold_reason_is_logged(capsys):
    from test_v845_fir_one_trace import init
    app,observer,engine,hub,fir=init()
    try:
        fir.warning("FIR cần đúng 1 Trace tick đã xác minh trong Smaart")
        assert "V8124_TOOL_NOTICE FIRDialog FIR cần đúng 1 Trace" in capsys.readouterr().out
    finally:
        hub.close();app.processEvents()
