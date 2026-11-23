"""Calibrate RemiX MAG preview to native bright Smaart reference magnitude.

The TF sum is H1+H2. This module ONLY estimates a display offset aligning
the unchanged REF magnitude samples with a native cyan/teal magnitude trace.
A correct match lets the physically computed SUM sit above REF by ~6dB for
equal-amplitude coherent signals. No +6dB hack and no DSP gain mutation.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import win32gui
from full_scan_v7 import printwindow_image
from trf_core import matched
from tf_display_smoothing import smooth_log_octaves

@dataclass(frozen=True)
class MagAnchor:
    offset_db:float
    score:float
    alternative_score:float
    bins:int
    accepted:bool
    reason:str

def _cyan_native_mask(rgb):
    a=np.asarray(rgb.convert("RGB"),dtype=np.uint8)
    r=a[:,:,0].astype(np.int16)
    g=a[:,:,1].astype(np.int16)
    b=a[:,:,2].astype(np.int16)
    native=(b>105)&(g>83)&(b>r+50)&(g>r+25)&(b>g*.87)
    native[:10]=0;native[-5:]=0
    native[:,:38]=0
    native[:,max(0,a.shape[1]-310):]=0
    return native

def _spread(mask,radius=3):
    rad=int(radius)
    padded=np.pad(mask.astype(np.int32),((rad,rad),(rad,rad)))
    z=np.pad(padded,((1,0),(1,0))).cumsum(0).cumsum(1)
    k=rad*2+1
    out=z[k:,k:]-z[:-k,k:]-z[k:,:-k]+z[:-k,:-k]
    return out>0

def fit_magnitude_ref(image,mag_rect,win_rect,ref,other,
                      display_ymin,display_ymax,mag_oct=1/6,
                      min_bins=55):
    x,y,w,h=map(int,mag_rect)
    wl,wt,_,_=map(int,win_rect)
    if display_ymax<=display_ymin or w<500 or h<150:
        return MagAnchor(0,0,0,0,False,"Invalid Y geometry")
    rgb=image.crop((x-wl,y-wt,x-wl+w,y-wt+h))
    mask=_cyan_native_mask(rgb)
    if int(mask.sum())<250:
        return MagAnchor(0,0,0,0,False,"Cyan source not visible")
    thick=_spread(mask)
    f,h1,_,coh=matched(ref,other)
    db=20*np.log10(np.maximum(abs(h1),1e-15))
    if mag_oct:
        db=smooth_log_octaves(f,db,mag_oct)
    xx=np.rint(w*np.log(np.maximum(f,1e-6)/20.)/np.log(1000.)).astype(int)
    valid=(np.isfinite(db)&(f>=60)&(f<=1800)&(coh>=.60)
           &(xx>44)&(xx<w-320))
    if valid.sum()<min_bins:
        return MagAnchor(0,0,0,int(valid.sum()),False,"Insufficient REF bins")
    xx=xx[valid]
    db=db[valid]
    # Unknown magnitude display offset. This is a pure transform to Smaart
    # native y pixels and must not be applied to any complex measurement.
    offsets=np.arange(-145.,61.,.25)
    yy=np.rint(
        ((float(display_ymax)-(db[None,:]+offsets[:,None]))/
         (float(display_ymax)-float(display_ymin)))*h
    ).astype(int)
    inside=(yy>=2)&(yy<h-2)
    yy=np.clip(yy,2,h-3)
    scored=thick[yy,xx[None,:]] & inside
    scores=scored.mean(axis=1)
    ix=int(np.argmax(scores))
    chosen=float(offsets[ix])
    best=float(scores[ix])
    distant=np.abs(offsets-chosen)>=4.
    alt=float(scores[distant].max()) if distant.any() else 0.
    # Tight match in multiple regions: prevents matching the wrong line,
    # or an accidental crop occupied by UI/overlay.
    third=max(1,len(xx)//3)
    matches=scored[ix]
    chunks=[float(z.mean()) for z in np.array_split(matches,3)]
    ok=best>=.66 and best-alt>=.18 and min(chunks)>=.44
    reason=("Matched native bright cyan REF" if ok
            else f"Ambiguous native magnitude: {best:.2f}, alt {alt:.2f}, thirds {chunks}")
    return MagAnchor(chosen,best,alt,len(xx),ok,reason)

def capture_mag_ref(hwnd,mag_rect,ref,other,lo,hi,mag_oct=1/6):
    rect=win32gui.GetWindowRect(hwnd)
    im=printwindow_image(hwnd)
    return fit_magnitude_ref(im,mag_rect,rect,ref,other,lo,hi,mag_oct)
