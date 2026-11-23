"""Low-latency relative Phase viewport tracker using native Smaart pixels.

A small GDI ROI captures colored Smaart traces (not RemiX neon SUM), and
two independent vertical row-signatures determine signed Y translation.
No FFT processing or native Smaart app modification. The slower absolute
REF-to-native fit is used only as an anchor when movement pauses.
"""
from __future__ import annotations
from dataclasses import dataclass
import time
import numpy as np
from fast_phase_y_v80 import DesktopRoiCapture

@dataclass(frozen=True)
class PanFrame:
    delta_px:float
    confidence:float
    valid:bool
    reason:str
    capture_ms:float
    frame_time:float

def colored_profiles(image):
    pix=np.asarray(image.convert("RGB"),dtype=np.uint8)
    r,g,b=(pix[:,:,j].astype(np.int16) for j in range(3))
    # Native Smaart Mag can be pure #FF0000 (G~0). The old (g>30)
    # clause wrongly excluded that original red trace while still showing
    # RemiX's green SUM. Accept saturated native red and blue/cyan, never green.
    native=((b>75)&(b>r*1.45)&(b>g*.68)) | (
             (r>130)&(r>g*1.7)&(r>b*1.4)&(g<150))
    native[:8]=False
    native[-3:]=False
    mid=native.shape[1]//2
    # Downsample horizontal pixels only. Preserve 1px vertical precision.
    masks=(native[:,:mid:3],native[:,mid::3])
    profiles=tuple(z.sum(axis=1).astype(float) for z in masks)
    return (profiles,masks),int(native.sum())

def best_vertical_shift(before,after,limit=90):
    """C-vectorized zero-mean cross-correlation, not ~200 Python loops."""
    a=np.asarray(before,dtype=float)
    b=np.asarray(after,dtype=float)
    if a.shape!=b.shape or a.ndim!=1 or len(a)<150:
        return None,0.
    n=len(a)
    a=a-a.mean()
    b=b-b.mean()
    corr=np.correlate(b,a,mode="full")
    steps=np.arange(-min(limit,n//3),min(limit,n//3)+1)
    idx=n-1+steps
    asq=np.r_[0,np.cumsum(a*a)]
    bsq=np.r_[0,np.cumsum(b*b)]
    al=np.where(steps>=0,0,-steps)
    ar=np.where(steps>=0,n-steps,n)
    bl=np.where(steps>=0,steps,0)
    br=np.where(steps>=0,n,n+steps)
    denom=np.sqrt(np.maximum((asq[ar]-asq[al])*(bsq[br]-bsq[bl]),1e-12))
    q=corr[idx]/denom
    i=int(np.argmax(q))
    return int(steps[i]),float(q[i])

def _pixel_score(a,b,dy):
    h=a.shape[0]
    if dy>0:
        x=a[:h-dy];y=b[dy:]
    elif dy<0:
        x=a[-dy:];y=b[:h+dy]
    else:
        x=a;y=b
    aa=int(x.sum());bb=int(y.sum())
    if aa<20 or bb<20:return 0.
    return float(np.count_nonzero(x&y)/np.sqrt(aa*bb))

def infer_pan(prev,current):
    if prev is None or current is None:
        return PanFrame(0.,0.,False,"No baseline",0.,time.monotonic())
    before_profiles,before_masks=prev
    after_profiles,after_masks=current
    shifts=[]
    ambiguous=False
    for pa,pb,a,b in zip(before_profiles,after_profiles,
                         before_masks,after_masks):
        coarse,_=best_vertical_shift(pa,pb)
        if coarse is None:
            return PanFrame(0.,0.,False,"Invalid row signature",0.,time.monotonic())
        # Fast path: a narrow 2D refinement around the row-density peak.
        candidates=set(range(max(-89,coarse-4),min(89,coarse+4)+1))
        candidates.update(range(-5,6))
        scored=[(_pixel_score(a,b,k),k) for k in candidates]
        best,dy=max(scored)
        zero=_pixel_score(a,b,0)
        ambiguous |= best<.42 or (abs(dy)>0 and best-zero<.055)
        shifts.append((dy,best))
    disagreement=abs(shifts[0][0]-shifts[1][0])>2
    confidence=min(x[1] for x in shifts)
    if ambiguous or disagreement or confidence<.85:
        # Wrapped Phase stripes can bias the 1D peak by ~10px, especially
        # during upward pan. Retry 2D alignment only on rejected/weak
        # frames; ordinary 60Hz native tracking keeps the original fast path.
        centers=[v[0] for v in shifts]
        candidates={k for center in centers
                    for k in range(max(-89,center-12),min(89,center+12)+1)}
        best_common=(0.,0)
        for dy in candidates:
            quality=min(_pixel_score(a,b,dy)
                        for a,b in zip(before_masks,after_masks))
            if quality>best_common[0]:
                best_common=(quality,dy)
        if best_common[0]>=.85 and (
                ambiguous or disagreement or best_common[0]>confidence+.05):
            return PanFrame(float(best_common[1]),best_common[0],True,
                            "Native 2D signed-pan recovery",0.,time.monotonic())
        if ambiguous:
            return PanFrame(0.,confidence,False,"Native pixel movement ambiguous",
                            0.,time.monotonic())
        if disagreement:
            return PanFrame(0.,confidence,False,
                            "Independent native regions disagree",
                            0.,time.monotonic())
    return PanFrame(float(round(sum(z[0] for z in shifts)/2)),
                    confidence,True,"Native pixel pan",
                    0.,time.monotonic())

class NativeFastPan:
    """Call poll only on one dedicated executor thread."""
    def __init__(self):
        self.dc=None;self.key=None;self.prev=None
    def poll(self,key,phase_rect):
        start=time.perf_counter()
        if self.dc is None:self.dc=DesktopRoiCapture()
        x,y,w,h=map(int,phase_rect)
        # Exclude ruler and right RemiX side panel; still span both LF/HF.
        off=max(65,int(w*.105))
        width=min(int(w*.65),w-off-290,
                  int(getattr(self,"sample_width",1000000)))
        if width<280 or h<180:
            return PanFrame(0.,0.,False,"Unsupported plot geometry",
                            0.,time.monotonic())
        image=self.dc.capture(x+off,y, width,h)
        profiles,pixels=colored_profiles(image)
        elapsed=(time.perf_counter()-start)*1000
        if pixels<200:
            self.prev=None;self.key=key
            return PanFrame(0.,0.,False,"Native pixels hidden",
                            elapsed,time.monotonic())
        if self.key!=key or self.prev is None:
            self.prev=profiles;self.key=key
            return PanFrame(0.,1.,True,"baseline",elapsed,time.monotonic())
        ans=infer_pan(self.prev,profiles)
        self.prev=profiles
        return PanFrame(ans.delta_px,ans.confidence,ans.valid,ans.reason,
                        (time.perf_counter()-start)*1000,time.monotonic())
