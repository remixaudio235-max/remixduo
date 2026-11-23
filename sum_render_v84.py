"""Low-latency discontinuity-aware SUM TF polyline topology (QA V8.4).

- Physical complex H and true coherence are not modified.
- Mag: draw physical complex magnitude even in low-coherence bins, but faint;
  preserve crossings at Y viewport edge instead of deleting endpoints.
- Phase: model unit-phase smoothing for trusted bins, unsmoothed fallback
  (already present in SumTrace.phase_deg) in unreliable bins, faint.
  Split proper 360° wrap at the Y top/bottom, never draw a diagonal wrap.
- Break only for genuinely missing/nonfinite data or large gaps in frequency.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class Edge:
    x0:float
    y0:float
    x1:float
    y1:float
    quality:str

@dataclass(frozen=True)
class Geometry:
    edges:tuple[Edge,...]
    high_edges:int
    low_edges:int
    wrap_splits:int
    clipped_edges:int
    data_gaps:int

def _clip_y(x0,y0,x1,y1,height):
    """Exact clipping against top/bottom, retaining crossing endpoints."""
    if not all(np.isfinite(v) for v in (x0,y0,x1,y1)):
        return None
    top,bottom=0.,float(height)
    if (y0<top and y1<top) or (y0>bottom and y1>bottom):
        return None
    if abs(y1-y0)<1e-10:
        return (x0,y0,x1,y1) if top<=y0<=bottom else None
    if y0<top or y0>bottom:
        crossing=top if y0<top else bottom
        t=(crossing-y0)/(y1-y0)
        x0,y0=x0+t*(x1-x0),crossing
    if y1<top or y1>bottom:
        crossing=top if y1<top else bottom
        t=(crossing-y0)/(y1-y0)
        x1,y1=x0+t*(x1-x0),crossing
    return (x0,y0,x1,y1)

def make_geometry(hz,values,good,fmin,fmax,ymin,ymax,
                  width,height,kind,max_gap_px=23.):
    hz=np.asarray(hz,dtype=float)
    values=np.asarray(values,dtype=float)
    good=np.asarray(good,dtype=bool)
    if hz.ndim!=1 or hz.shape!=values.shape or hz.shape!=good.shape:
        raise ValueError("SUM data shape mismatch")
    if not (fmin>0 and fmax>fmin and width>0 and height>0 and ymax>ymin):
        return Geometry((),0,0,0,0,0)
    denominator=np.log(float(fmax)/float(fmin))
    fgood=np.isfinite(hz)&(hz>=fmin)&(hz<=fmax)&np.isfinite(values)
    if not np.any(fgood):
        return Geometry((),0,0,0,0,0)
    x=width*np.log(np.maximum(hz,1e-30)/float(fmin))/denominator
    span=ymax-ymin
    wrap=(kind=="phase" and 350.<=span<=370.)
    if wrap:
        yval=(values-ymin)%360. + ymin
    else:
        yval=values.copy()
    canvas_y=(ymax-yval)*height/span
    edges=[]
    wraps=clipped=gaps=0
    last_index=None
    high_edges=low_edges=0
    def add(px0,py0,px1,py1,quality):
        nonlocal clipped,high_edges,low_edges
        visible=_clip_y(float(px0),float(py0),float(px1),float(py1),height)
        if visible is None:
            clipped+=1
            return
        edges.append(Edge(*visible,quality))
        if quality=="high":high_edges+=1
        else:low_edges+=1
    for i in range(len(hz)):
        if not fgood[i]:
            last_index=None
            continue
        if last_index is None:
            last_index=i
            continue
        j=last_index
        last_index=i
        dx=x[i]-x[j]
        if not np.isfinite(dx) or dx<=0 or dx>max_gap_px:
            gaps+=1
            continue
        quality="high" if good[i] and good[j] else "low"
        if wrap:
            v0,v1=yval[j],yval[i]
            step=v1-v0
            # shortest circular arc; avoids diagonal phase line through plot
            if step>180.:v1-=360.
            elif step<-180.:v1+=360.
            if v1>ymax:
                frac=(ymax-v0)/(v1-v0)
                xc=x[j]+frac*dx
                add(x[j],canvas_y[j],xc,0.,quality)
                add(xc,float(height),x[i],canvas_y[i],quality)
                wraps+=1
                continue
            if v1<ymin:
                frac=(ymin-v0)/(v1-v0)
                xc=x[j]+frac*dx
                add(x[j],canvas_y[j],xc,float(height),quality)
                add(xc,0.,x[i],canvas_y[i],quality)
                wraps+=1
                continue
        add(x[j],canvas_y[j],x[i],canvas_y[i],quality)
    return Geometry(tuple(edges),high_edges,low_edges,wraps,clipped,gaps)
