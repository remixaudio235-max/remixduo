"""V8.168 QA: serialize heavy proof worker submissions without caching proof."""
from concurrent.futures import Future
from native_poll_budget_v8162 import native_proof_busy


class FakeNativeScheduler:
    def __init__(self,drag=False):
        self.axis_future=None
        self.mag_anchor_future=None
        self.offset_future=None
        self.axis_drag=object() if drag else None
        self.submitted=[]
    def _schedule_absolute_axis_calibration(self,target):
        if "phase" not in self.submitted:
            self.submitted.append("phase")
            self.axis_future=Future()
    def _schedule_mag_ref_anchor(self,target):
        if "mag" not in self.submitted:
            self.submitted.append("mag")
            self.mag_anchor_future=Future()
    def _schedule_trace_offsets(self,target):
        if "offsets" not in self.submitted:
            self.submitted.append("offsets")
            self.offset_future=Future()


def schedule(obj):
    from overlay_v7 import App
    App._schedule_steady_native_proofs(obj,object())


def test_native_busy_accepts_none_and_finished_futures_only():
    a=Future()
    assert not native_proof_busy(None,None,None)
    assert native_proof_busy(None,a,None)
    a.set_result("never a proof permission")
    assert not native_proof_busy(None,a,None)


def test_serializes_phase_mag_and_offsets_even_when_all_due():
    d=FakeNativeScheduler()
    schedule(d)
    assert d.submitted==["phase"]
    schedule(d)
    assert d.submitted==["phase"]
    d.axis_future.set_result(None)
    schedule(d)
    assert d.submitted==["phase","mag"]
    schedule(d)
    assert d.submitted==["phase","mag"]
    d.mag_anchor_future.set_result(None)
    schedule(d)
    assert d.submitted==["phase","mag","offsets"]
    assert native_proof_busy(d.axis_future,d.mag_anchor_future,d.offset_future)


def test_drag_bypasses_nonurgent_phase_axis_but_keeps_order():
    d=FakeNativeScheduler(drag=True)
    schedule(d)
    assert d.submitted==["mag"]
    d.mag_anchor_future.set_result(None)
    schedule(d)
    assert d.submitted==["mag","offsets"]
    assert "phase" not in d.submitted


def test_completed_native_future_does_not_serve_as_cached_proof():
    d=FakeNativeScheduler()
    done=Future()
    done.set_result({"accepted": False})
    d.axis_future=done
    d.submitted=["phase"]
    schedule(d)
    assert d.submitted==["phase","mag"]
