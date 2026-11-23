"""V8.165 native magnitude fit for curves clipped by the Y viewport.

Invoked only as an optional fallback from trace_offset_native_v8114.
Caller MUST verify the same captured native 0 dB grid and live smoothing.
No cached native proof, no relaxation of source identity or Export gate.
"""
from __future__ import annotations
import numpy as np
from smaart_native_mag_fit import NativeMagFit,NativeMagFrame

MIN_VISIBLE_COVERAGE=.65
MIN_VISIBLE_PER_BAND=20
MIN_VISIBLE_SCORE=.82
MIN_PER_BAND_SCORE=.65
MIN_ALTERNATIVE_MARGIN=.14
GRID_SCALE_TOLERANCE=.04


def _reject(reason,bins=0,score=0.,alternative=0.):
    return NativeMagFit(0.,0.,0.,float(score),float(alternative),
                        int(bins),False,reason)


def fit_clipped_grid(image,plot_rect,window_rect,freq_hz,mag_db,coh,
                     *,y_min,y_max,color,frame=None):
    """Score only visible predicted points, with three-band coverage gates.

    Grid MUST be verified beforehand. Optimized scale is constrained to
    +/- 4% of the independent native-grid px/dB; alternative models compete
    at a physically distinct center >=18 px away.
    """
    x,y,w,h=map(int,plot_rect)
    l,t,r,b=map(int,window_rect)
    span=float(y_max)-float(y_min)
    if not(w>=900 and h>=240 and x>=l and y>=t and
           x+w<=r and y+h<=b and 8.<span<150. and
           np.isfinite(span)):
        return _reject("Unverified native grid geometry")
    native_scale=h/span
    if not np.isfinite(native_scale) or native_scale<=0.:
        return _reject("Invalid native grid scale")
    frame=frame or NativeMagFrame(image,plot_rect,window_rect)
    if not frame.matches(image,plot_rect,window_rect):
        return _reject("Native image/viewport changed")
    thick=frame.expanded(color)
    if thick is None:
        return _reject("Native source color missing")
    f=np.asarray(freq_hz,float).reshape(-1)
    db=np.asarray(mag_db,float).reshape(-1)
    coherence=np.asarray(coh,float).reshape(-1)
    if not(len(f)==len(db)==len(coherence) and len(f)>=55
           and np.all(np.isfinite(f)) and np.all(np.diff(f)>0)
           and np.all(np.isfinite(db)) and np.all(np.isfinite(coherence))):
        return _reject("Malformed source TF")
    xx=np.rint(w*np.log(np.maximum(f,1e-10)/20.)/np.log(1000.)).astype(int)
    ids=np.flatnonzero((f>=60)&(f<=1800)&(xx>46)&(xx<w-320))
    if len(ids)<55:
        return _reject("Insufficient trusted native frequency bins",len(ids))
    if np.ptp(np.percentile(db[ids],[5,95]))<1.5:
        return _reject("Source shape cannot identify Y offset",len(ids))
    if len(ids)>240:
        ids=ids[np.rint(np.linspace(0,len(ids)-1,240)).astype(int)]
    xs=xx[ids]
    source_median=float(np.median(db[ids]))
    z=db[ids]-source_median
    groups=np.array_split(np.arange(len(ids)),3)
    centers=np.arange(8,h-8,dtype=float)
    # Evaluate every grid-constrained center and scale exactly as before,
    # but vectorize the visibility/three-band gate instead of constructing
    # thousands of Python tuples and calling NumPy once per candidate.
    candidate_scores=[]
    candidate_centers=[]
    candidate_scales=[]
    candidate_visible=[]
    candidate_bands=[]
    for scale in native_scale*np.linspace(1-GRID_SCALE_TOLERANCE,
                                          1+GRID_SCALE_TOLERANCE,9):
        yy=np.rint(centers[:,None]-z[None,:]*scale).astype(np.int32)
        visible=(yy>=4)&(yy<h-5)
        hits=thick[np.clip(yy,3,h-4),xs[None,:]] & visible
        visible_count=visible.sum(axis=1)
        group_visible=np.column_stack(
            tuple(visible[:,g].sum(axis=1) for g in groups))
        eligible=(visible_count>=MIN_VISIBLE_COVERAGE*len(ids)) & (
            group_visible.min(axis=1)>=MIN_VISIBLE_PER_BAND)
        ids_ok=np.flatnonzero(eligible)
        if not len(ids_ok):
            continue
        group_hits=np.column_stack(
            tuple(hits[:,g].sum(axis=1) for g in groups))
        candidate_scores.append(
            hits.sum(axis=1)[ids_ok]/np.maximum(visible_count[ids_ok],1))
        candidate_centers.append(centers[ids_ok])
        candidate_scales.append(np.full(len(ids_ok),scale,dtype=float))
        candidate_visible.append(visible_count[ids_ok])
        candidate_bands.append(
            group_hits[ids_ok]/np.maximum(group_visible[ids_ok],1))
    if not candidate_scores:
        return _reject("Native trace clipped beyond minimum observable coverage",
                       len(ids))
    all_scores=np.concatenate(candidate_scores)
    all_centers=np.concatenate(candidate_centers)
    all_scales=np.concatenate(candidate_scales)
    all_visible=np.concatenate(candidate_visible)
    all_bands=np.concatenate(candidate_bands)
    best_index=int(np.argmax(all_scores))
    score=float(all_scores[best_index])
    center=float(all_centers[best_index])
    scale=float(all_scales[best_index])
    nvisible=int(all_visible[best_index])
    bands=[float(v) for v in all_bands[best_index]]
    distinct=np.abs(all_centers-center)>=18.
    alternate=float(np.max(all_scores[distinct])) if np.any(distinct) else 0.
    accepted=bool(score>=MIN_VISIBLE_SCORE
                  and min(bands)>=MIN_PER_BAND_SCORE
                  and score-alternate>=MIN_ALTERNATIVE_MARGIN)
    reason=("Native clipped grid/source match" if accepted else
            f"Native clipped proof HOLD score={score:.3f}, "
            f"alternative={alternate:.3f}, bands={bands}, "
            f"visible={nvisible}/{len(ids)}")
    return NativeMagFit(center,scale,source_median,score,alternate,
                        nvisible,accepted,reason)
