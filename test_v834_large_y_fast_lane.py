"""V8.34: real App callbacks, >89px gesture and stale worker fail-closed."""
import time
from types import SimpleNamespace
import pytest
from PyQt6.QtWidgets import QApplication
import overlay_v7
from overlay_v7 import App
from native_fast_pan_v81 import PanFrame
from native_dual_y_v82 import DualPanResult


@pytest.fixture
def active(monkeypatch):
    app=QApplication.instance() or QApplication([])
    e=App(False)
    e.timer.stop();e.drag_timer.stop()
    e.current_sum=object()
    e.current_pair=('A','B')
    e.plot_hwnd=41
    e.plot_layout=SimpleNamespace(phase=(252,84,1442,412),
                                  mag=(252,539,1442,412))
    e._mag_anchor_verified=True
    e.graph_mag.native_axis_ready=True
    e.graph_phase.y_min=-180.;e.graph_phase.y_max=180.
    e.graph_mag.y_min=-20.;e.graph_mag.y_max=20.
    cursor=[230,300]
    down=[False]
    monkeypatch.setattr(overlay_v7.win32api,'GetCursorPos',lambda:tuple(cursor))
    monkeypatch.setattr(overlay_v7.win32api,'GetAsyncKeyState',
                        lambda _:0x8000 if down[0] else 0)
    target=SimpleNamespace(hwnd=41)
    yield e,cursor,down,target,app
    e.timer.stop();e.drag_timer.stop()
    e.axis_drag=None;e.mag_axis_drag=None
    e.hide()


@pytest.mark.parametrize('kind,change', [('phase',160),('mag',180)])
def test_large_signed_move_and_round_trip_without_jumps(active,kind,change):
    e,cursor,down,target,app=active
    original=e.current_sum
    graph=e.graph_phase if kind=='phase' else e.graph_mag
    check=e._check_phase_axis_drag if kind=='phase' else e._check_mag_axis_drag
    base=(graph.y_min,graph.y_max)
    rect=getattr(e.plot_layout,kind)
    cursor[:]=[rect[0]-22,rect[1]+rect[3]//2]
    check(target)
    down[0]=True
    check(target)
    state=e.axis_drag if kind=='phase' else e.mag_axis_drag
    assert state is not None
    previous_epoch=e._viewport_epoch
    previous_max=graph.y_max
    cursor[1]+=change
    check(target)
    assert graph.y_max==pytest.approx(base[1]), "Mouse-only motion is not native pan"
    # Four genuine 40/45px native Y movements fit the 89px tracker cap.
    def send_native(dy):
        time.sleep(.035)
        good=PanFrame(float(dy),.99,True,"native confirmed",1.,time.monotonic())
        weak=PanFrame(0.,0.,False,"other axis",1.,time.monotonic())
        currentkey=(41,e.plot_layout.phase,e.plot_layout.mag,
                    e.current_pair,e._reference_index(),e._viewport_epoch)
        pack=DualPanResult(good,weak) if kind=="phase" else DualPanResult(weak,good)
        e.on_native_dual_pan((currentkey,pack))
    for _ in range(4):send_native(change/4.)
    assert graph.y_max==pytest.approx(
        base[1]+change*(base[1]-base[0])/rect[3])
    assert graph.y_max>previous_max
    # Native relative capture from BEFORE drag must be rejected, not
    # superimposed on the 180px local preview during mouse hold.
    stale=PanFrame(-72.,.99,True,'prior sample',1.,time.monotonic())
    oldkey=(41,e.plot_layout.phase,e.plot_layout.mag,e.current_pair,
            e._reference_index(),previous_epoch-1)
    pan_before=(e.graph_phase.y_max,e.graph_mag.y_max)
    e.on_native_dual_pan((oldkey,DualPanResult(stale,stale)))
    assert (e.graph_phase.y_max,e.graph_mag.y_max)==pan_before
    cursor[1]-=change
    check(target)
    assert graph.y_max>base[1], "Pointer return without native movement must not snap"
    for _ in range(4):send_native(-change/4.)
    assert graph.y_min==pytest.approx(base[0])
    assert graph.y_max==pytest.approx(base[1])
    down[0]=False
    check(target)
    assert e._viewport_epoch>previous_epoch
    assert graph.y_max==pytest.approx(base[1])
    assert e.current_sum is original


def test_independent_phase_and_mag_axes(active):
    e,cursor,down,target,app=active
    cursor[:]=[230,745]
    down[0]=True
    e._check_phase_axis_drag(target)
    e._check_mag_axis_drag(target)
    assert e.axis_drag is None
    assert e.mag_axis_drag is not None
    cursor[1]+=160
    e._check_mag_axis_drag(target)
    assert e.graph_phase.y_max==180.
    assert e.graph_mag.y_max==20., "Mag must not follow pointer without native trace"
    key=(41,e.plot_layout.phase,e.plot_layout.mag,e.current_pair,
         e._reference_index(),e._viewport_epoch)
    for _ in range(4):
        time.sleep(.035)
        stamp=time.monotonic()
        good=PanFrame(40.,.99,True,"verified source",1.,stamp)
        none=PanFrame(0.,0.,False,"not moved",1.,stamp)
        e.on_native_dual_pan((key,DualPanResult(none,good)))
    assert e.graph_phase.y_max==180.
    assert e.graph_mag.y_max>30.
    down[0]=False
    e._check_mag_axis_drag(target)
    assert e.mag_axis_drag is None


def test_click_on_chart_does_not_drag_sum(active):
    e,cursor,down,target,app=active
    down[0]=True
    cursor[:]=[900,720]
    e._check_phase_axis_drag(target)
    e._check_mag_axis_drag(target)
    assert e.axis_drag is None
    assert e.mag_axis_drag is None
    assert e.graph_phase.y_max==180.
    assert e.graph_mag.y_max==20.
