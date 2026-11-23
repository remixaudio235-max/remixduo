"""V8.52 practical speaker-tuning PEQ policy: enforce Q 3..8.

Supports conservative high-confidence *cut-only* cleanup using free
PEQ slots after the core solver and V8.50 spacing have finished.
Never widen old narrow Q=16 filters by merely rewriting Q.
"""
from __future__ import annotations
import numpy as np
from scipy.signal import find_peaks
from .autoeq_engine import (
    AutoEQBand,biquad_response,prepare_analysis_curves,compute_metrics,
    cascade_biquads)
from .spacing import close_pairs,MIN_SPACING_OCT
from .peak_shape import refine_cut_peak_shoulder

Q_MIN=3.0
Q_MAX=8.0


def q_in_bounds(bands):
    return all(Q_MIN-1e-8 <= float(b.q) <= Q_MAX+1e-8 for b in bands)


def safely_fill_residual_peaks(inp,profile,bands,after,target,*,status,
                               max_new=2):
    """Add up to 2 coherent cut bands using unused max PEQ budget.

    Every candidate must improve weighted error without creating an
    excessive new adjacent dip, exceed gain/ROI/Q/spacing, or alter
    the original transfer function. Failure is a no-op.
    """
    bands=tuple(bands)
    after=np.asarray(after,float)
    target=np.asarray(target,float)
    if (status!="PREVIEW_READY" or not q_in_bounds(bands) or
            len(bands)>=profile.max_filters or
            after.shape!=target.shape):
        return bands,after,()
    data=prepare_analysis_curves(inp,profile)
    freq=data.grid_hz
    if len(freq)!=len(after) or not np.isfinite(after).all():
        return bands,after,()
    trusted=(freq>=profile.f_min_hz)&(freq<=profile.f_max_hz)&(
        data.quality>=.80)&(data.reliability>=.70)&(
        ~data.deep_null_mask)&(data.weights>1e-5)
    if trusted.sum()<16:
        return bands,after,()
    original=after.copy()
    warnings=[]
    added_count=0
    for _ in range(min(max_new,int(profile.max_filters)-len(bands))):
        res=after-target
        peaks,_=find_peaks(res,prominence=1.5,height=2.5)
        candidates=[int(i) for i in peaks if trusted[i] and
                    all(abs(np.log2(freq[i]/b.f_hz))>=MIN_SPACING_OCT
                        for b in bands)]
        if not candidates:break
        candidates=sorted(candidates,key=lambda i:-res[i])[:6]
        old_metrics=compute_metrics(data,target,after,bands)
        protected=trusted&(res<=-1.5)
        best=None
        for i in candidates:
            center=float(freq[i])
            for factor in (.985,1.,1.015):
                fc=center*factor
                if not profile.f_min_hz<=fc<=profile.f_max_hz:continue
                if any(abs(np.log2(fc/b.f_hz))<MIN_SPACING_OCT for b in bands):
                    continue
                for q in (4.,5.,6.,7.,8.):
                    if q<profile.min_q or q>profile.max_resonance_q:continue
                    for g in (-2.5,-3.5,-4.5,-5.5,-6.5,-7.5,-8.5):
                        if g<profile.max_cut_db:continue
                        band=AutoEQBand("P",fc,float(g),q)
                        correction=20*np.log10(np.maximum(abs(
                            biquad_response(freq,band,data.sample_rate)),1e-15))
                        pred=after+correction
                        if protected.any() and float(np.min(
                                (pred-after)[protected]))<-1.25:
                            continue
                        met=compute_metrics(data,target,pred,bands+(band,))
                        if (met.weighted_rms_db>old_metrics.weighted_rms_db-.025
                                or met.p90_abs_error_db>old_metrics.p90_abs_error_db+.32
                                or met.worst_abs_error_db>old_metrics.worst_abs_error_db+.30):
                            continue
                        now_peak=float(pred[i]-target[i])
                        if (float(res[i])-now_peak<1.5 or
                                now_peak < -1.0 or now_peak > 2.0):
                            continue
                        neighborhood=trusted&(
                            abs(np.log2(freq/center))<=.14)
                        if np.sum(neighborhood)<3:continue
                        top_after=float(np.max((pred-target)[neighborhood]))
                        top_before=float(np.max(res[neighborhood]))
                        if top_before-top_after<1.0:continue
                        score=(met.weighted_rms_db+
                               .055*max(top_after-1.,0.)+
                               .008*abs(now_peak),
                               met.weighted_rms_db,abs(now_peak),fc,q,g)
                        if best is None or score<best[0]:
                            best=(score,band,pred,float(res[i]),now_peak)
        if best is None:break
        band=best[1]
        band,pred,shape_warning=refine_cut_peak_shoulder(
            data,target,after,band,bands,profile)
        bands+= (band,)
        added_count+=1
        after=pred
        old_peak=float(np.interp(best[1].f_hz,freq,res))
        new_peak=float(np.interp(best[1].f_hz,freq,after-target))
        warnings.append(f"PRACTICAL_Q_3_8_PEAK: {band.f_hz:.0f}Hz, "
                        f"{old_peak:+.2f}->{new_peak:+.2f}dB, "
                        "free PEQ slot, preview only")
        if shape_warning:warnings.append(shape_warning)
    if not warnings:return bands,original,()
    if close_pairs(bands) or not q_in_bounds(bands):
        raise ValueError("Practical-Q filter topology invariant broken")
    old_eq=cascade_biquads(freq,bands[:-added_count],data.sample_rate)
    new_eq=cascade_biquads(freq,bands,data.sample_rate)
    source_mag=original-20*np.log10(np.maximum(abs(old_eq),1e-15))
    corrected=source_mag+20*np.log10(np.maximum(abs(new_eq),1e-15))
    if not np.allclose(after,corrected,atol=1e-7):
        raise ValueError("Practical-Q prediction/cascade parity broken")
    return bands,corrected,tuple(warnings)
