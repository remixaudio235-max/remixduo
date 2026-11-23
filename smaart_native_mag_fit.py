# -*- coding: utf-8 -*-
"""Read-only, confidence-gated registration of native Smaart MAG pixels.

Fit the stored bright-cyan REF magnitude to Smaart's original plot pixels;
never infer scale from the AutoPhase GUI, display dB guess, or a mouse drag.
Absolute transform is y_px = y_center - (Mag_db - source_median)*px_per_db.
No Smaart write, no DLL injection, no audio I/O.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from PIL import Image
import ctypes, win32gui, win32ui

@dataclass(frozen=True)
class NativeMagFit:
    center_px:float
    px_per_db:float
    source_median_db:float
    score:float
    alternative_score:float
    bins:int
    accepted:bool
    reason:str

    def y(self,mag_db):
        return self.center_px-(np.asarray(mag_db,dtype=float)-self.source_median_db)*self.px_per_db

def capture_native_window(hwnd):
    """PrintWindow(PW_RENDERFULLCONTENT), read-only image of original Smaart HWND."""
    l,t,r,b=win32gui.GetWindowRect(hwnd)
    w,h=r-l,b-t
    if not(820<w<10000 and 550<h<10000):
        raise RuntimeError("Smaart size invalid")
    dc_h=win32gui.GetWindowDC(hwnd)
    dc=win32ui.CreateDCFromHandle(dc_h)
    mem=dc.CreateCompatibleDC()
    bmp=win32ui.CreateBitmap()
    old=None
    try:
        bmp.CreateCompatibleBitmap(dc,w,h)
        old=mem.SelectObject(bmp)
        ok=ctypes.windll.user32.PrintWindow(hwnd,mem.GetSafeHdc(),2)
        if not ok:raise RuntimeError("Smaart PrintWindow failed")
        raw=bmp.GetBitmapBits(True)
        im=Image.frombuffer("RGB",(w,h),raw,"raw","BGRX",0,1).copy()
        # V8.113: sparse blank check (full-frame float64 std was ~45 MB/call).
        if np.asarray(im.reduce(8),dtype=np.uint8).std()<3:
            raise RuntimeError("Smaart screenshot blank")
        return im,(l,t,r,b)
    finally:
        try:
            if old is not None: mem.SelectObject(old)
            win32gui.DeleteObject(bmp.GetHandle())
        except Exception:pass
        try:mem.DeleteDC()
        except Exception:pass
        finally:
            # GetWindowDC must be released via ReleaseDC; calling CDC.DeleteDC
            # on this externally owned HDC can fail and prevent ReleaseDC.
            win32gui.ReleaseDC(hwnd,dc_h)

def _hsv(r,g,b):
    r=r.astype(np.float32)/255.;g=g.astype(np.float32)/255.;b=b.astype(np.float32)/255.
    mx=np.maximum(np.maximum(r,g),b);mn=np.minimum(np.minimum(r,g),b);d=mx-mn
    safe=np.where(d>1e-6,d,1.)
    h=np.where(mx==r,((g-b)/safe)%6,np.where(mx==g,(b-r)/safe+2,(r-g)/safe+4))*60.
    s=np.where(mx>1e-6,d/np.maximum(mx,1e-6),0.)
    return np.where(d>1e-6,h,0.),s,mx


def _hex_color_mask(r,g,b,color):
    """V8.130: mask for a trace's OWN Smaart colour (Data Bar icon '#RRGGBB').

    Hue within 16 deg of the icon hue, clearly coloured (not grid/white/grey),
    not too dark. Covers Smaart colours outside the fixed palette (live:
    slate blue #6677A8 matched none of the 7 named masks).
    """
    c=color.lstrip("#")
    cr,cg,cb=(np.array([int(c[i:i+2],16)]) for i in (0,2,4))
    ch,cs,cv=(float(x[0]) for x in _hsv(cr,cg,cb))
    h,s,v=_hsv(r,g,b)
    dh=np.abs((h-ch+180.)%360.-180.)
    return (dh<=16.)&(s>=max(.18,cs*.5))&(v>=max(.22,cv*.45))


def trace_color_mask(im,color="cyan"):
    ar=np.asarray(im.convert("RGB"),dtype=np.uint8)
    r=ar[:,:,0].astype(np.int16);g=ar[:,:,1].astype(np.int16);b=ar[:,:,2].astype(np.int16)
    if isinstance(color,str) and color.startswith("#") and len(color)==7:
        mask=_hex_color_mask(r,g,b,color)
    elif color=="cyan":
        # Native bright cyan has blue ~= green or bluer. On Smaart8
        # Light, antialiased DARK teal RGB(0,115,95) can satisfy the old
        # b>g*.87 predicate and create a false cyan/teal score tie.
        # Keep the two source-color identities disjoint at the hue boundary.
        mask=(b>105)&(g>83)&(b>r+50)&(g>r+25)&(b>=g*.96)&(g>=b*.70)
    elif color=="red":
        # V8.129: pink/magenta traces (live TUNNINNGGG ~160,48,112) also
        # passed this mask and tied with "magenta" (score 1.0 both) -> the
        # FIR preview stayed HOLD forever. Real reds have little blue.
        mask=(r>110)&(r>g*1.55)&(r>b*1.45)&(g<125)&(b<r*.5)
    elif color=="blue":
        mask=(b>85)&(b>r*1.50)&(b>g*1.45)&(g<b*.70)&(r<110)
    elif color=="teal":
        # Smaart Suite 9 turquoise TF curve (observed RGB 27,224,166).
        # Distinct from cyan (blue near green) and olive green (low blue).
        # QA Dark: real native Smaart8 teal is RGB(0,115,95) on BOTH
        # skins, not the bright Suite teal (27,224,166). Preserve the
        # independent hue/contrast constraints while accepting this actual
        # native line; source shape/fit confidence gates stay unchanged.
        mask=(g>105)&(b>84)&(r<95)&(g>b*1.10)&(g<b*1.50)&(g-r>75)&(b-r>65)
    elif color=="green":
        # R60: Smaart 8's native olive TF is very dark/antialiased. On a
        # captured 1366x768 native plot, the true curve was RGB(64,94,64)
        # down to (35,49,35). The old g-b>=30 threshold retained only 45
        # pixels (<250 required), hiding BOTH SUM Mag and SUM Phase despite
        # a valid TRF. This relaxed color mask only proposes green pixels;
        # score/alternative/thirds, two-X-hypothesis and source identity
        # checks in fit_native_mag/select_smaart8_native_axis stay intact.
        # Neutral grid/white remain excluded by positive chroma deltas.
        mask=((g>=40)&(g>r*1.25)&(g>b*1.17)&
              (g-r>=13)&(g-b>=12)&(r<150)&(b<125))
    elif color=="magenta":
        # Native Smaart magenta (R+B dominant) is absent from legacy palette.
        mask=(r>100)&(b>95)&(r>g*1.65)&(b>g*1.55)
    elif color=="gold":
        # Gold / amber Smaart traces; do not include red or yellow grid labels.
        mask=(r>80)&(g>50)&(r>b*2.3)&(g>b*2.0)&(r>g*.95)&(r<g*3.0)
    else:
        raise ValueError("Unknown native trace color")
    mask[:10]=0;mask[-5:]=0
    mask[:,:38]=0;mask[:,max(0,ar.shape[1]-310):]=0
    return mask

def cyan_mask(im):
    return trace_color_mask(im,"cyan")

def expand(mask,radius=3):
    """Exact square dilation with two boolean passes, not int64 integrals.

    Pixel-wise OR is mathematically identical to the old 7x7 summed-area
    expansion, but avoids allocating multiple >5MB int64 arrays per color.
    """
    if radius<0:raise ValueError("Dilation radius must be nonnegative")
    src=np.asarray(mask,dtype=bool)
    if src.ndim!=2:raise ValueError("Native color mask must be 2D")
    horizontal=src.copy()
    for shift in range(1,min(radius,max(0,src.shape[1]-1))+1):
        horizontal[:,shift:] |= src[:,:-shift]
        horizontal[:,:-shift] |= src[:,shift:]
    result=horizontal.copy()
    for shift in range(1,min(radius,max(0,src.shape[0]-1))+1):
        result[shift:,:] |= horizontal[:-shift,:]
        result[:-shift,:] |= horizontal[shift:,:]
    return result

class NativeMagFrame:
    """One-capture-only, identity-bound color masks for multiple TF fits.

    Expanding a 1442x440 boolean mask using int64 image integrals per TF
    created large temporary allocations. Reuse it within THIS screenshot,
    not across a later Smaart tick, HWND, Y viewport or source revision.
    This class does not provide any verification score or export permission.
    """
    def __init__(self,image,plot_rect,window_rect):
        self.image=image
        self.plot_rect=tuple(map(int,plot_rect))
        self.window_rect=tuple(map(int,window_rect))
        x,y,w,h=self.plot_rect
        l,t,r,b=self.window_rect
        self.valid=(w>=820 and h>=210 and x>=l and y>=t
                    and x+w<=r and y+h<=b)
        self.roi=(image.crop((x-l,y-t,x-l+w,y-t+h))
                  if self.valid else None)
        self._masks={}
        self._thick={}

    def matches(self,image,plot_rect,window_rect):
        return (self.valid and image is self.image and
                tuple(map(int,plot_rect))==self.plot_rect and
                tuple(map(int,window_rect))==self.window_rect)

    def _mask(self,color):
        if color not in self._masks:
            self._masks[color]=trace_color_mask(self.roi,color)
        return self._masks[color]

    def visible_colors(self,colors,minimum_pixels=250):
        if not self.valid:return ()
        return tuple(color for color in colors
                     if np.count_nonzero(self._mask(color))>=minimum_pixels)

    def expanded(self,color):
        if not self.valid:return None
        if np.count_nonzero(self._mask(color))<250:
            return None
        if color not in self._thick:
            self._thick[color]=expand(self._mask(color),3)
        return self._thick[color]


def _reject(reason,n=0,score=0,alternative=0):
    return NativeMagFit(0,0,0,float(score),float(alternative),int(n),False,reason)

def fit_native_mag(image,plot_rect,window_rect,frequencies,mag_db,coherence,
                   *,min_bins=55,expect_x_min=20.,expect_x_max=20000.,
                   trace_color="cyan",frame=None):
    x,y,w,h=map(int,plot_rect)
    l,t,r,b=map(int,window_rect)
    if not(w>=820 and h>=210 and x>=l and y>=t and x+w<=r and y+h<=b):
        return _reject("Invalid native Mag plot bounds")
    if frame is None:
        native=image.crop((x-l,y-t,x-l+w,y-t+h))
        mask=trace_color_mask(native,trace_color)
        if np.count_nonzero(mask)<250:
            return _reject(f"{trace_color} REF curve missing")
        thick=expand(mask,3)
    else:
        # A precomputed mask is trusted ONLY for the exact same PIL image
        # object and native plot/window geometry. No cross-frame cache.
        if not isinstance(frame,NativeMagFrame) or not frame.matches(
                image,plot_rect,window_rect):
            return _reject("Native frame image/geometry mismatch")
        thick=frame.expanded(trace_color)
        if thick is None:
            return _reject(f"{trace_color} REF curve missing")
    f=np.asarray(frequencies,float).reshape(-1)
    db=np.asarray(mag_db,float).reshape(-1)
    coh=np.asarray(coherence,float).reshape(-1)
    if not(len(f)==len(db)==len(coh) and len(f)>=55 and
           np.all(np.isfinite(f)) and np.all(np.diff(f)>0) and
           np.all(np.isfinite(db)) and np.all(np.isfinite(coh))):
        return _reject("Malformed source TF")
    xx=np.rint(w*np.log(np.maximum(f,1e-10)/expect_x_min)/
              np.log(expect_x_max/expect_x_min)).astype(int)
    # V8.135: native Auto EQ grounding follows the visible magnitude trace;
    # coherence is metadata and must not prevent fitting a low-coherence TF.
    good=(f>=60)&(f<=1800)&(xx>46)&(xx<w-320)&np.isfinite(db)
    # Reject low-dynamic-range REF, where native pixels can't identify Y scale.
    ids=np.flatnonzero(good)
    if len(ids)<min_bins:return _reject("Insufficient trusted REF bins",len(ids))
    if np.ptp(np.percentile(db[ids],[5,95]))<1.5:
        return _reject("REF lacks Y-scale identifying structure",len(ids))
    # Downsample for performance while keeping spatial coverage.
    if len(ids)>240:
        ids=ids[np.rint(np.linspace(0,len(ids)-1,240)).astype(int)]
    xs=xx[ids]; ys_db=db[ids]
    median=float(np.median(ys_db))
    z=ys_db-median
    def evaluate(scales,centers):
        best=(-1.,0.,0.,None)
        for scale in scales:
            yy=np.rint(centers[:,None]-z[None,:]*scale).astype(int)
            inside=(yy>=4)&(yy<h-5)
            yi=np.clip(yy,3,h-4)
            hit=thick[yi,xs[None,:]] & inside
            score=hit.mean(axis=1)
            ii=int(score.argmax())
            candidate=(float(score[ii]),float(centers[ii]),float(scale),hit[ii])
            if candidate[0]>best[0]:best=candidate
        return best
    # Search Y scale independently from saved Smaart settings. A zoom/scroll
    # changes the axis; incorrect scale must not be extrapolated from old XML.
    scales=h/np.linspace(18.,90.,37)
    centers=np.arange(9,h-9,3)
    coarse=evaluate(scales,centers)
    near_scales=np.linspace(coarse[2]*.91,coarse[2]*1.09,21)
    near_centers=np.arange(max(5,int(coarse[1])-12),min(h-5,int(coarse[1])+13))
    best=evaluate(near_scales,near_centers)
    bestscore,center,scale,bits=best
    # Evaluate alternative *distant* models to avoid matching a wrong trace.
    alt=0.
    for s in scales[::2]:
        cc=centers
        yy=np.rint(cc[:,None]-z[None,:]*s).astype(int)
        inside=(yy>=4)&(yy<h-5)
        yi=np.clip(yy,3,h-4)
        score=(thick[yi,xs[None,:]]&inside).mean(axis=1)
        distinct=(np.abs(cc-center)>=18)|(np.abs(s-scale)/scale>=.23)
        if distinct.any(): alt=max(alt,float(score[distinct].max()))
    groups=np.array_split(bits,3)
    thirds=[float(group.mean()) for group in groups]
    accepted=(bestscore>=.68 and bestscore-alt>=.14 and
              min(thirds)>=.40 and 0<scale<=h/12.)
    reason=("Matched native Smaart cyan REF" if accepted else
            f"Ambiguous REF/Y fit score={bestscore:.2f} alternative={alt:.2f} thirds={thirds}")
    return NativeMagFit(center,scale,median,bestscore,alt,len(ids),accepted,reason)

def native_points(plot_rect,fit,frequencies,db_values,coherence,
                  *,expect_x_min=20,expect_x_max=20000):
    """Grounded absolute pixels of corrected EQ curve. No guessed Y viewport."""
    x,y,w,h=map(int,plot_rect)
    f=np.asarray(frequencies,float)
    db=np.asarray(db_values,float)
    coh=np.asarray(coherence,float)
    if not fit.accepted or f.shape!=db.shape or f.shape!=coh.shape:
        return np.empty((0,2)),np.empty((0,),bool)
    xx=x+w*np.log(np.maximum(f,1e-10)/expect_x_min)/np.log(expect_x_max/expect_x_min)
    yy=y+fit.y(db)
    valid=(f>=expect_x_min)&(f<=expect_x_max)&np.isfinite(xx)&np.isfinite(yy)
    points=np.column_stack((xx[valid],yy[valid]))
    trust=coh[valid]>=.60
    return points,trust
