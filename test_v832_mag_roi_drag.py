"""V8.32: LF/HF draggable full-height in Mag AND Phase, one ROI source."""
from types import SimpleNamespace
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF, QEvent
from PyQt6.QtGui import QMouseEvent
from overlay_v7 import App
from roi_markers_v73 import hz_to_x


def drag(grip,x):
    y=max(9,grip.height()//2)
    start=QPointF(grip.x()+grip.width()/2,grip.y()+y)
    end=QPointF(float(x),grip.y()+y)
    grip.mousePressEvent(QMouseEvent(
        QEvent.Type.MouseButtonPress,QPointF(grip.width()/2,y),start,
        Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier))
    grip.mouseMoveEvent(QMouseEvent(
        QEvent.Type.MouseMove,QPointF(grip.width()/2,y),end,
        Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier))
    grip.mouseReleaseEvent(QMouseEvent(
        QEvent.Type.MouseButtonRelease,QPointF(grip.width()/2,y),end,
        Qt.MouseButton.LeftButton,Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier))
    assert not grip.dragging


def test_mag_and_phase_can_drag_shared_lf_hf():
    app=QApplication.instance() or QApplication([])
    engine=App(False)
    engine.timer.stop()
    engine._selection_verified=True
    engine.current_sum=object()
    original=engine.current_sum
    phase=(252,84,1200,380)
    mag=(252,539,1200,380)
    engine.plot_layout=SimpleNamespace(phase=phase,mag=mag)
    engine._apply_plot_layout()
    app.processEvents()
    try:
        assert set(engine.roi_line_grips)=={'LF','HF'}
        assert set(engine.mag_roi_line_grips)=={'LF','HF'}
        assert all(grip.isVisible() for grip in engine.mag_roi_line_grips.values())
        assert all(grip.isVisible() for grip in engine.roi_line_grips.values())
        for key in ('LF','HF'):
            a=engine.roi_line_grips[key];b=engine.mag_roi_line_grips[key]
            assert a.y()==phase[1]+29
            assert a.height()==phase[3]-29
            assert b.y()==mag[1]
            assert b.height()==mag[3]
            assert b.width()==17
            assert b.cursor().shape()==Qt.CursorShape.SizeHorCursor
        engine.last_solve=[object()]
        drag(engine.mag_roi_line_grips['LF'],hz_to_x(90,mag[0],mag[2]))
        app.processEvents()
        assert abs(engine.lf.value()-90)<0.2
        assert engine.last_solve is None
        assert abs(engine.graph_mag.lf_hz-90)<0.2
        assert abs(engine.graph_phase.lf_hz-90)<0.2
        assert engine.current_sum is original
        assert abs(engine.mag_roi_line_grips['LF'].x()+8-
                   hz_to_x(90,mag[0],mag[2]))<2
        assert abs(engine.roi_line_grips['LF'].x()+8-
                   hz_to_x(90,phase[0],phase[2]))<2
        drag(engine.mag_roi_line_grips['HF'],hz_to_x(400,mag[0],mag[2]))
        assert abs(engine.hf.value()-400)<2
        drag(engine.roi_line_grips['HF'],hz_to_x(500,phase[0],phase[2]))
        assert abs(engine.hf.value()-500)<2
        # Preserve ordering under attempted LF/HF crossing.
        drag(engine.mag_roi_line_grips['LF'],hz_to_x(900,mag[0],mag[2]))
        assert engine.lf.value()<engine.hf.value()
        # Different native plot X bounds must use the drag SOURCE plot.
        phase2=(120,100,1000,390)
        mag2=(250,550,1200,340)
        engine.plot_layout=SimpleNamespace(phase=phase2,mag=mag2)
        engine._apply_plot_layout()
        drag(engine.mag_roi_line_grips['HF'],hz_to_x(1000,mag2[0],mag2[2]))
        assert abs(engine.hf.value()-1000)<3
        # Workspace switches must not leave active hit windows over Mag.
        engine.overlay_workspace_visible=False
        engine.refresh_visibility()
        assert not any(g.isVisible() for g in engine.mag_roi_line_grips.values())
        assert not any(g.isVisible() for g in engine.roi_line_grips.values())
    finally:
        for grip in (*engine.roi_line_grips.values(),
                     *engine.mag_roi_line_grips.values()):
            grip.hide()
        engine.timer.stop()
        engine.close()
