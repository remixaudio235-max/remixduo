"""Tests for GUI connection of the native Smaart Phase Y-ruler gesture."""
import time
from types import SimpleNamespace
import pytest
import overlay_v7
from overlay_v7 import App

def harness():
    x=SimpleNamespace(
        plot_layout=SimpleNamespace(phase=(252,112,1442,398)),
        current_sum=object(),
        graph_phase=SimpleNamespace(y_min=-180.,y_max=180.),
        axis_drag=None,_axis_was_pressed=False,
        _phase_axis_generation=5,_phase_pan_last_frame=0.,
        pan_last_move=0.,axis_requested=9.,
    )
    x.moves=[]
    x._apply_phase_pan=lambda move,state:x.moves.append((move,state["lo"],state["hi"]))
    return x

def test_real_axis_press_drag_release_reanchors(monkeypatch):
    a=harness()
    cursor=[230,300]; pressed=[False]
    monkeypatch.setattr(overlay_v7.win32api,'GetCursorPos',lambda:tuple(cursor))
    monkeypatch.setattr(overlay_v7.win32api,'GetAsyncKeyState',
                        lambda key:0x8000 if pressed[0] else 0)
    target=SimpleNamespace(hwnd=123)
    App._check_phase_axis_drag(a,target)
    assert a.axis_drag is None
    pressed[0]=True
    App._check_phase_axis_drag(a,target)
    assert a.axis_drag is not None
    assert a._phase_axis_generation==6
    cursor[1]+=36
    App._check_phase_axis_drag(a,target)
    # Mouse-only movement must not spoof a Smaart native Phase axis pan.
    assert a.moves==[]
    assert a.axis_drag['preview_shift']==36.
    pressed[0]=False
    App._check_phase_axis_drag(a,target)
    assert a.axis_drag is None
    assert a._phase_axis_generation==7
    assert a.axis_requested==0
    assert abs(time.monotonic()-a.pan_last_move)<.25

def test_non_axis_click_is_not_treated_as_phase_pan(monkeypatch):
    a=harness()
    cursor=[900,300]; pressed=[True]
    monkeypatch.setattr(overlay_v7.win32api,'GetCursorPos',lambda:tuple(cursor))
    monkeypatch.setattr(overlay_v7.win32api,'GetAsyncKeyState',lambda key:0x8000)
    App._check_phase_axis_drag(a,SimpleNamespace(hwnd=123))
    assert a.axis_drag is None
    assert a._phase_axis_generation==5
    assert a.moves==[]

def test_loss_of_native_data_clears_gesture_state(monkeypatch):
    a=harness();a.axis_drag={"start":(230,300)}
    a.current_sum=None
    App._check_phase_axis_drag(a,SimpleNamespace(hwnd=123))
    assert a.axis_drag is None
