"""Passive Smaart Phase Y viewport observer — monitors actual native traces.

No dependence on mouse position, focus history, or drag event delivery.
The source is native Smaart PrintWindow output only (blue/cyan pixels).
Only translational Y panning is supported; zoom/trace edit is fail-closed.
"""
from __future__ import annotations
import numpy as np
from phase_axis_follow_v77 import (
    native_blue_mask, capture_native_phase, detect_vertical_shift,
    PanObservation, shifted_y_range,
)

def infer_native_pan(before,after,limit=270):
    """Require full and two independent halves to agree on a real Y shift."""
    a=np.asarray(before,dtype=bool)
    b=np.asarray(after,dtype=bool)
    if a.shape!=b.shape or a.ndim!=2 or a.shape[1]<120:
        return PanObservation(0.,0.,False,"Invalid image geometry")
    # A pan should move both independent native Trace regions by the same
    # number of pixels. A new Trace, zoom or repaint usually will not.
    whole=detect_vertical_shift(a,b,max_shift=limit)
    if not whole.valid:
        return whole
    dy=whole.shift_px
    if abs(dy)<2:
        return PanObservation(0.,whole.confidence,True,"No significant viewport movement")
    mid=a.shape[1]//2
    checks=[]
    for sl in (slice(0,mid),slice(mid,None)):
        x=a[:,sl];y=b[:,sl]
        test=detect_vertical_shift(x,y,max_shift=limit)
        if not test.valid or abs(test.shift_px-dy)>3:
            return PanObservation(0.,whole.confidence,False,
                                  "Native Trace regions disagree (zoom/replot)")
        checks.append(test.confidence)
    if min(checks)<.45:
        return PanObservation(0.,whole.confidence,False,"Insufficient subregion agreement")
    # Disambiguate periodic phase curves: the shifted correspondence should
    # be meaningfully more convincing than 0 shift.
    if dy>=0:
        x=a[:a.shape[0]-int(dy)]
        y=b[int(dy):]
    else:
        x=a[-int(dy):]
        y=b[:a.shape[0]+int(dy)]
    total=np.sqrt(max(1,np.count_nonzero(a))*max(1,np.count_nonzero(b)))
    zero=np.count_nonzero(a&b)/total
    improvement=(np.count_nonzero(x&y)/total)-zero
    if improvement<.045:
        return PanObservation(0.,whole.confidence,False,
                              "Shift not distinguishable from redraw")
    return PanObservation(dy,whole.confidence,True,
                          "Confirmed passive Smaart Phase Y pan")

class NativeAxisFollower:
    """Runs on one dedicated worker: stores baseline per plot/Trace identity."""
    def __init__(self):
        self.key=None
        self.previous=None
        self.captures=0

    def sample(self,key,hwnd,phase_rect):
        current=capture_native_phase(hwnd,phase_rect)
        self.captures+=1
        if key!=self.key or self.previous is None:
            self.key=key
            self.previous=current
            return None
        result=infer_native_pan(self.previous,current)
        # Always advance to newest observed native Smaart state, but only
        # propagate strong, agreed translational movement to Qt.
        self.previous=current
        return result
