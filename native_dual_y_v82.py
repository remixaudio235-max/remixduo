"""One native-image worker for BOTH Smaart TF plot Y axes.

The Phase and Magnitude axes are independently identified and corrected.
Same read-only GDI device context, same thread, independent pixel histories.
"""
from __future__ import annotations
from dataclasses import dataclass
from native_fast_pan_v81 import NativeFastPan,PanFrame


def native_pan_poll_interval(active_kind, seconds_since_gesture):
    """Keep fast ruler gestures; avoid 30Hz dual PrintWindow fits at rest.

    Passive Smaart mouse-wheel/viewport edits are still observed at 5-6Hz.
    All pixel/source/viewport proof stays in NativeFastPan.poll().
    """
    if active_kind in ("mag", "phase"):
        return 0.025
    if float(seconds_since_gesture)<0.9:
        return 0.075
    return 0.18

@dataclass(frozen=True)
class DualPanResult:
    phase:PanFrame
    mag:PanFrame

class NativeDualFastPan:
    def __init__(self):
        self.phase=NativeFastPan()
        self.mag=NativeFastPan()
        # Compact native ROIs retain independent Smaart polylines while
        # reducing GDI readback and 2D fine-match computation.
        self.phase.sample_width=440
        self.mag.sample_width=440
    def poll(self,key,phase_rect,mag_rect,active_kind=None):
        # An active Smaart ruler needs only its own plot pixels. Avoid a
        # second unnecessary screenshot/correlation inside fast gesture.
        import time
        inactive=lambda:PanFrame(0.,0.,False,"Inactive plot",0.,time.monotonic())
        phase=(self.phase.poll((key,"phase"),phase_rect)
               if active_kind in (None,"phase") else inactive())
        if self.mag.dc is None and self.phase.dc is not None:
            self.mag.dc=self.phase.dc
        mag=(self.mag.poll((key,"mag"),mag_rect)
             if active_kind in (None,"mag") else inactive())
        return DualPanResult(phase,mag)
