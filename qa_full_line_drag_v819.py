"""V8.19: LF/HF dashed-line drag QA (Phase plot, not the top labels)."""
from pathlib import Path
from types import SimpleNamespace
from PyQt6.QtCore import Qt,QEvent,QPointF
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from roi_markers_v73 import ROIMarker,ROILineGrip,hz_to_x
from trf_core import read_trf
import win32gui

def drag_line(grip,local_y,new_global_x):
    # Same event phases as an actual user drawing horizontally on the
    # dashed guide at arbitrary Y; plot is never clicked/modified.
    pos=grip.pos()
    mid=grip.width()/2
    start_global=QPointF(pos.x()+mid,pos.y()+local_y)
    target_global=QPointF(float(new_global_x),float(pos.y()+local_y))
    press=QMouseEvent(QEvent.Type.MouseButtonPress,
                      QPointF(mid,local_y),start_global,
                      Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,
                      Qt.KeyboardModifier.NoModifier)
    grip.mousePressEvent(press)
    assert grip.dragging
    move=QMouseEvent(QEvent.Type.MouseMove,QPointF(mid,local_y),
                     target_global,Qt.MouseButton.NoButton,
                     Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    grip.mouseMoveEvent(move)
    release=QMouseEvent(QEvent.Type.MouseButtonRelease,
                        QPointF(mid,local_y),target_global,
                        Qt.MouseButton.LeftButton,Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier)
    grip.mouseReleaseEvent(release)
    assert not grip.dragging

app=QApplication([])
w=App(demo=False)
w.timer.stop()
files=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
pair=(read_trf(files/"SUb.trf"),read_trf(files/"FULL.trf"))
w.current_traces=pair
w.current_pair=tuple(str(t.path) for t in pair)
w.recalc()
source_sum=w.current_sum
assert source_sum is not None
phase=(250,110,1180,352)
mag=(250,500,1180,300)
w.plot_layout=SimpleNamespace(phase=phase,mag=mag)
w._apply_plot_layout()
app.processEvents()
assert set(w.roi_line_grips)=={"LF","HF"}
for name in ("LF","HF"):
    grip=w.roi_line_grips[name]
    marker=w.roi_markers[name]
    hz=w.lf.value() if name=="LF" else w.hf.value()
    assert grip.isVisible() and marker.isVisible()
    assert grip.width()==17
    assert grip.y()==phase[1]+ROIMarker.HEIGHT
    assert grip.height()==phase[3]-ROIMarker.HEIGHT
    assert abs(grip.x()+grip.width()//2-hz_to_x(hz,phase[0],phase[2]))<=1.1
    assert grip.cursor().shape()==Qt.CursorShape.SizeHorCursor
    assert not (grip.windowFlags()&Qt.WindowType.WindowTransparentForInput)
    assert grip.windowFlags()&Qt.WindowType.WindowDoesNotAcceptFocus
    print("FULL_HEIGHT_HITBOX_PASS",name,grip.geometry().getRect(),flush=True)
    # On native Windows, the grip must actually own the pixel under
    # the cursor (not pass through as a 100%-transparent window).
    try:
        center=(grip.x()+grip.width()//2,grip.y()+grip.height()//2)
        target=win32gui.WindowFromPoint(center)
        hwnd=int(grip.winId())
        print("NATIVE_HIT_TEST",name,"wanted",hwnd,"got",target,flush=True)
        if __import__("sys").platform=="win32":
            assert target==hwnd,("Grip is not Win32 hit-testable",name,hwnd,target)
    except Exception as e:
        raise AssertionError(str(e)) from e

axis_before=(w.phase_min.value(),w.phase_max.value())
w.last_solve=[object()]
lf=w.roi_line_grips["LF"]
drag_line(lf,lf.height()//2,round(hz_to_x(95,phase[0],phase[2])))
app.processEvents()
assert abs(w.lf.value()-95)<.2,w.lf.value()
assert w.last_solve is None
assert w.current_sum is source_sum
assert (w.phase_min.value(),w.phase_max.value())==axis_before
assert abs(w.roi_line_grips["LF"].x()+8-hz_to_x(w.lf.value(),phase[0],phase[2]))<2
print("DRAG_MIDDLE_LF_PASS",w.lf.value(),flush=True)

hf=w.roi_line_grips["HF"]
drag_line(hf,hf.height()-12,round(hz_to_x(400,phase[0],phase[2])))
app.processEvents()
assert abs(w.hf.value()-400)<1.3,w.hf.value()
assert w.current_sum is source_sum
assert abs(w.graph_phase.hf_hz-w.hf.value())<1e-6
assert abs(w.graph_mag.hf_hz-w.hf.value())<1e-6
print("DRAG_BOTTOM_HF_PASS",w.hf.value(),flush=True)

# Existing top text grips remain freely draggable.
assert all(m.isVisible() for m in w.roi_markers.values())
# Crossing is blocked by existing ROI physical constraints.
drag_line(lf,lf.height()-9,round(hz_to_x(1300,phase[0],phase[2])))
assert w.lf.value()<w.hf.value()
print("LF_HF_CROSSING_GUARD_PASS",w.lf.value(),w.hf.value(),flush=True)

# Smaart swaps Mag/Phase panels => full-height grips follow actual Phase.
new_phase=(250,503,1180,310)
w.plot_layout=SimpleNamespace(phase=new_phase,mag=(250,110,1180,350))
w._apply_plot_layout()
app.processEvents()
for grip in w.roi_line_grips.values():
    assert grip.y()==new_phase[1]+ROIMarker.HEIGHT
    assert grip.height()==new_phase[3]-ROIMarker.HEIGHT
print("PLOT_SWAP_PHASE_FOLLOWS_PASS",flush=True)
# Loss of plot/TF => no lingering invisible window intercepting clicks.
w.on_plot_layout(None)
app.processEvents()
assert not any(g.isVisible() for g in w.roi_line_grips.values())
print("INVALID_LAYOUT_FAIL_CLOSED_PASS",flush=True)
w.close()
app.processEvents()
print("V819_LF_HF_ANYWHERE_ON_DASHED_LINE_ALL_PASS",flush=True)
