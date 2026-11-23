"""Absolute Smaart Phase viewport calibration against the *fixed REF* trace.

The native Smaart plot does not expose live Y bounds via UI Automation.
Rather than accumulating guessed mouse movements, compare the complex
source REF phase to ORIGINAL Smaart colored pixels in its Phase chart.
Fit the modulo-360 viewport top, with strict confidence and contrast
gates; repaint only SUM Y, preserving complex FFT data and AutoAlign.

Assumes a 360-degree Phase viewport; zoom scale mismatch is NOT certified.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import win32gui
from full_scan_v7 import printwindow_image
from tf_display_smoothing import smooth_phase_unit_phasor
from trf_core import matched

@dataclass(frozen=True)
class AxisFit:
    top_deg:float
    bottom_deg:float
    hit_fraction:float
    alternate_fraction:float
    bins:int
    accepted:bool
    reason:str

def _colored_traces(image,w,h):
    arr=np.asarray(image.convert("RGB"),dtype=np.uint8)
    if arr.shape[0]!=h or arr.shape[1]!=w:
        raise ValueError("Smaart chart geometry changed during capture")
    r=arr[:,:,0].astype(np.int16)
    g=arr[:,:,1].astype(np.int16)
    b=arr[:,:,2].astype(np.int16)
    # Native Smaart dark blue/cyan and muted red/brown trace polylines.
    # Deliberately exclude neon green overlays and neutral grid lines.
    native=((b>75)&(b>r*1.45)&(b>g*.68)) | (
             (r>95)&(r>g*1.20)&(r>b*.85)&(g>30))
    native[:12]=False
    native[-3:]=False
    native[:,:35]=False
    native[:,max(0,w-330):]=False
    return native

def _dilate_9(mask,radius=4):
    """Summed-area table for a 9x9 neighbor hit, numpy-only O(pixels)."""
    rad=int(radius)
    padded=np.pad(mask.astype(np.int32),((rad,rad),(rad,rad)))
    z=np.pad(padded,((1,0),(1,0))).cumsum(0).cumsum(1)
    k=rad*2+1
    count=z[k:,k:]-z[:-k,k:]-z[k:,:-k]+z[:-k,:-k]
    assert count.shape==mask.shape
    return count>0

def fit_ref_phase_axis(
    native_image,phase_rect,window_rect,ref,other,
    center_top=180.,coh_gate=.6,phase_oct=1/6,
):
    """Find Y top by phase-template overlap, not mouse delta or stale XML."""
    x,y,w,h=map(int,phase_rect)
    wl,wt,wr,wb=map(int,window_rect)
    crop=(x-wl,y-wt,x-wl+w,y-wt+h)
    if min(w,h)<100:
        return AxisFit(0.,0.,0.,0.,0,False,"Invalid native plot geometry")
    mask=_colored_traces(native_image.crop(crop),w,h)
    if int(mask.sum())<400:
        return AxisFit(0.,0.,0.,0.,0,False,"Not enough native Phase pixels")
    dilated=_dilate_9(mask)
    f,h1,h2,coh=matched(ref,other)
    phase,valid,_=smooth_phase_unit_phasor(f,h1,coh,phase_oct,coh_gate)
    xx=np.rint(w*np.log(np.maximum(f,1e-6)/20.)/np.log(1000.)).astype(int)
    valid=(valid&(f>=30.)&(f<=3500.)&(xx>40)&(xx<w-340)
           &np.isfinite(phase))
    xs=xx[valid]
    phases=phase[valid]
    bins=len(xs)
    if bins<65:
        return AxisFit(0.,0.,0.,0.,bins,False,"Too few reliable REF phase bins")
    center=int(round(float(center_top)))
    candidates=np.arange(center-180,center+181,dtype=float)
    # Wrap each source phase into the 360-degree native plot window.
    y_px=np.rint(
        ((candidates[:,None]-phases[None,:])%360.0)*h/360.
    ).astype(int)
    y_px=np.clip(y_px,1,h-2)
    hit=dilated[y_px,xs[None,:]]
    quality=hit.mean(axis=1)
    best_i=int(np.argmax(quality))
    best=float(quality[best_i])
    chosen=float(candidates[best_i])
    circular_distance=np.abs(((candidates-chosen+180.)%360.)-180.)
    far=circular_distance>=35.
    alternative=float(quality[far].max()) if np.any(far) else 0.
    valid_fit=(best>=.72 and best-alternative>=.20)
    reason=("Matched native REF polyline" if valid_fit else
            f"Poor/ambiguous REF fit (hit={best:.2f}, other={alternative:.2f})")
    return AxisFit(chosen,chosen-360.,best,alternative,bins,valid_fit,reason)

def capture_fit(hwnd,phase_rect,ref,other,center_top=180.):
    win_rect=win32gui.GetWindowRect(hwnd)
    screenshot=printwindow_image(hwnd)
    return fit_ref_phase_axis(screenshot,phase_rect,win_rect,
                              ref,other,center_top=center_top)
