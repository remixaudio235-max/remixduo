"""During fast gestures only the relevant native chart is captured."""
import time
from native_dual_y_v82 import NativeDualFastPan
from native_fast_pan_v81 import PanFrame


def test_one_active_chart_no_extra_capture():
    tracker=NativeDualFastPan()
    calls=[]
    def phase(key,rect):
        calls.append('phase')
        return PanFrame(6.,.98,True,'source',.8,time.monotonic())
    def mag(key,rect):
        calls.append('mag')
        return PanFrame(-4.,.97,True,'source',.8,time.monotonic())
    tracker.phase.poll=phase
    tracker.mag.poll=mag
    for active,expected in [('phase',['phase']),('mag',['mag']),
                            (None,['phase','mag'])]:
        calls.clear()
        out=tracker.poll(('key',), (250,80,1000,400),
                         (250,500,1000,400),active)
        assert calls==expected
        if active=='phase':assert not out.mag.valid and out.phase.valid
        if active=='mag':assert not out.phase.valid and out.mag.valid
        if active is None:assert out.phase.valid and out.mag.valid
