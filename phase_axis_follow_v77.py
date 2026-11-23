"""Smaart Phase Y viewport follow, read-only and fail-closed.

The native Smaart plot's Y viewport is not exposed through UI Automation, and
SmaartConfig.xml is a stale saved state. We watch only a deliberate mouse drag
starting on the Phase Y axis ruler and compare two PrintWindow images of
Smaart's ORIGINAL cyan/blue trace pixels (ignoring green RemiX SUM pixels).
The resulting signed vertical displacement is applied to the SUM plot's
display Y transform. Raw H(f), Delay, Auto Align results and phase-match
statistics are not recomputed or changed.

This observes translational pan only. A scale/zoom change cannot be inferred
as a simple pan, and should not be treated as verified pixel parity.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import win32gui
from full_scan_v7 import printwindow_image

@dataclass(frozen=True)
class PanObservation:
    shift_px:float
    confidence:float
    valid:bool
    explanation:str

def native_blue_mask(image,phase_rect,window_rect):
    """Read blue/cyan ORIGINAL Smaart traces, not neon-green RemiX overlay."""
    x,y,w,h=phase_rect
    wl,wt,wr,wb=window_rect
    # Use uncluttered plot interior; avoid LEFT ticks and RIGHT RemiX panel.
    left=max(0,int(x-wl+max(24,w*.04)))
    right=min(image.width,int(x-wl+min(w-280,w*.74)))
    top=max(0,int(y-wt+4))
    bottom=min(image.height,int(y-wt+h-4))
    if right-left<160 or bottom-top<100:
        raise ValueError("Invalid Phase plot crop")
    rgb=np.asarray(image.crop((left,top,right,bottom)),dtype=np.uint8)
    # Stride 2x horizontally; keep all Y pixels for 1px phase pan precision.
    rgb=rgb[:,::2,:]
    r=rgb[:,:,0].astype(np.int16)
    g=rgb[:,:,1].astype(np.int16)
    b=rgb[:,:,2].astype(np.int16)
    # Smaart's cyan/blue lines: high blue, relatively low red; green neon
    # SUM has low blue and is deliberately excluded.
    mask=(b>85)&(b>r+34)&(b>g*.76)
    return mask

def detect_vertical_shift(before,after,max_shift=150):
    """Compare native blue-trace pixels, returning signed vertical shift.

    Positive shift = Smaart trace visually moved DOWN. Quality threshold
    ensures unknown changes are never declared a proven pan.
    """
    a=np.asarray(before,dtype=bool)
    b=np.asarray(after,dtype=bool)
    if a.shape!=b.shape or a.ndim!=2 or min(a.shape)<50:
        return PanObservation(0.,0.,False,"Geometry changed")
    if min(np.count_nonzero(a),np.count_nonzero(b))<160:
        return PanObservation(0.,0.,False,"Too few native phase pixels")
    rows=a.shape[0]
    max_shift=max(1,min(int(max_shift),int(rows*.72)))
    scores=[]
    for dy in range(-max_shift,max_shift+1):
        if dy>=0:
            aa=a[:rows-dy,:]
            bb=b[dy:,:]
        else:
            aa=a[-dy:,:]
            bb=b[:rows+dy,:]
        overlap=np.count_nonzero(aa&bb)
        mass=np.sqrt(max(1,np.count_nonzero(aa))*max(1,np.count_nonzero(bb)))
        scores.append(overlap/mass)
    scores=np.asarray(scores,dtype=float)
    idx=int(np.argmax(scores))
    shift=idx-max_shift
    quality=float(scores[idx])
    # Other uncorrelated redraws, no pan or newly switched Trace set
    # must not be promoted as positive sync.
    if quality<.45:
        return PanObservation(0.,quality,False,"Insufficient native trace correlation")
    if abs(shift)==max_shift:
        return PanObservation(0.,quality,False,"Movement beyond tracking window")
    # If the best displacement is 0, no display transform is needed.
    return PanObservation(float(shift),quality,True,"Native Smaart phase trace correlation")

def shifted_y_range(lo,hi,height,shift_px):
    """Apply actual drawn-pixel pan without touching complex TF samples."""
    lo=float(lo);hi=float(hi);height=float(height);shift_px=float(shift_px)
    if not np.isfinite([lo,hi,height,shift_px]).all() or height<=0 or hi<=lo:
        raise ValueError("Invalid Phase viewport")
    delta=shift_px*(hi-lo)/height
    return lo+delta,hi+delta

def capture_native_phase(hwnd,phase_rect):
    win_rect=win32gui.GetWindowRect(hwnd)
    image=printwindow_image(hwnd)
    return native_blue_mask(image,phase_rect,win_rect)
