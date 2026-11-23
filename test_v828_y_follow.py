"""V8.28 signed Y following, stale-frame rejection and no TF mutation."""
from __future__ import annotations
from types import SimpleNamespace
import time
import pytest
from overlay_v7 import App
from native_fast_pan_v81 import PanFrame
from native_dual_y_v82 import DualPanResult
from axis_y_sync_v828 import translated_y_range, trusted_pan


class FakeSpin:
    def __init__(self): self.value=None; self.blocked=False
    def blockSignals(self,on): self.blocked=bool(on)
    def setValue(self,value): self.value=value


class FakeGraph:
    def __init__(self,lo,hi):self.y_min=lo;self.y_max=hi;self.paints=0
    def update(self):self.paints+=1


class FakeLabel:
    def setText(self,text):self.value=text


def rig():
    f=SimpleNamespace(
        current_sum=object(), current_pair=("TraceA","TraceB"),
        plot_hwnd=41,
        plot_layout=SimpleNamespace(phase=(250,100,1440,400),
                                    mag=(250,540,1440,400)),
        graph_phase=FakeGraph(-180.,180.),
        graph_mag=FakeGraph(-20.,20.),
        phase_min=FakeSpin(),phase_max=FakeSpin(),
        mag_min=FakeSpin(),mag_max=FakeSpin(),
        phase_axis_note=FakeLabel(),mag_axis_note=FakeLabel(),
        _phase_pan_last_frame=0.,_mag_pan_last_frame=0.,
        _phase_axis_generation=0,_mag_axis_generation=0,
        _mag_anchor_verified=True,
        axis_last_spin=0.,axis_last_status=0.,pan_last_log=0.,
        mag_pan_last_spin=0.,mag_pan_last_status=0.,mag_pan_last_log=0.,
        pan_last_move=0.,mag_pan_last_move=0.,
        pan_accepted=0,mag_pan_accepted=0,
        pan_rejected=0,mag_pan_rejected=0,
        _reference_index=lambda:0,
    )
    f._apply_native_y_delta=lambda kind, frame: App._apply_native_y_delta(f,kind,frame)
    f.on_native_fast_pan=lambda payload: App.on_native_fast_pan(f,payload)
    f.on_native_mag_pan=lambda payload: App.on_native_mag_pan(f,payload)
    return f


def pan(dy,confidence=.995,stamp=None,valid=True):
    return PanFrame(float(dy),float(confidence),valid,"Native pixel pan",
                    28.,time.monotonic() if stamp is None else float(stamp))


def phase_key(f):
    return (f.plot_hwnd,f.plot_layout.phase,f.current_pair,0)


def mag_key(f):
    return (f.plot_hwnd,f.plot_layout.mag,f.current_pair,0)


@pytest.mark.parametrize("kind,span", [("phase",360.),("mag",40.)])
def test_sum_moves_same_signed_pixels_and_returns_without_changing_tf(kind,span):
    f=rig();src=f.current_sum
    graph=f.graph_mag if kind=="mag" else f.graph_phase
    handler=f.on_native_mag_pan if kind=="mag" else f.on_native_fast_pan
    key=mag_key(f) if kind=="mag" else phase_key(f)
    initial=(graph.y_min,graph.y_max)
    handler((key,pan(+20,stamp=time.monotonic()-.12)))
    assert graph.y_max==pytest.approx(initial[1]+20*span/400)
    assert graph.paints==1
    handler((key,pan(-20,stamp=time.monotonic()-.03)))
    assert (graph.y_min,graph.y_max)==pytest.approx(initial)
    assert graph.paints==2
    assert f.current_sum is src


def test_independent_axes_and_stale_frames():
    f=rig()
    phase=pan(+15,stamp=time.monotonic()-.10)
    mag=pan(-30,stamp=time.monotonic()-.07)
    key=(f.plot_hwnd,f.plot_layout.phase,f.plot_layout.mag,f.current_pair,0)
    App.on_native_dual_pan(f,(key,DualPanResult(phase,mag)))
    assert f.graph_phase.y_max==pytest.approx(193.5)
    assert f.graph_mag.y_max==pytest.approx(17.)
    assert f._phase_axis_generation==1
    assert f._mag_axis_generation==1
    # A frame captured before the last accepted pan must not jerk the axis back.
    f.on_native_fast_pan((phase_key(f),pan(-60,stamp=phase.frame_time-.01)))
    f.on_native_mag_pan((mag_key(f),pan(+60,stamp=mag.frame_time-.01)))
    assert f.graph_phase.y_max==pytest.approx(193.5)
    assert f.graph_mag.y_max==pytest.approx(17.)
    assert f.pan_rejected>=1 and f.mag_pan_rejected>=1


def test_stale_weak_and_unverified_native_mag_are_not_applied():
    f=rig()
    f.on_native_fast_pan((phase_key(f),pan(20,stamp=time.monotonic()-1.)))
    f.on_native_mag_pan((mag_key(f),pan(20,confidence=.55)))
    assert f.graph_phase.paints==0
    assert f.graph_mag.paints==0
    f._mag_anchor_verified=False
    f.on_native_mag_pan((mag_key(f),pan(20)))
    assert f.graph_mag.y_max==20.
    assert f._mag_axis_generation==0


def test_outdated_absolute_phase_calibration_cannot_override_recent_pan():
    f=rig()
    f.axis_task_ms=[]
    f.axis_rejected=0
    f.axis_accepted=0
    f.pan_last_move=time.monotonic()-2.
    # Intended for generation 0, but native trace has since moved.
    old_key=(f.plot_hwnd,f.plot_layout.phase,f.current_pair,0,0)
    f._phase_axis_generation=1
    fake=SimpleNamespace(accepted=True,bottom_deg=-500.,top_deg=-140.)
    App.on_absolute_phase_axis(f,(old_key,fake))
    assert (f.graph_phase.y_min,f.graph_phase.y_max)==(-180.,180.)


def test_invalid_geometry_and_excessive_delta_fail_closed():
    assert translated_y_range(-180.,180.,400,20)==pytest.approx((-162.,198.,18.))
    for vals in ((-180,180,0,20),(-180,180,400,100),
                 (1,1,400,20),(float("nan"),180,400,5)):
        with pytest.raises(ValueError):translated_y_range(*vals)
    assert not trusted_pan(pan(90),time.monotonic())
