"""V8.49: cut-only residual peak rescue; independent of production AEQ solver.

Only an exhausted Flat-PEQ budget is eligible. Every replacement must
improve actual weighted RMS and the coherent local peak while protecting
nearby valleys, worst-error and P90 metrics. Fail closed otherwise.
"""
from __future__ import annotations
import numpy as np
from scipy.signal import find_peaks
from .autoeq_engine import (
    AutoEQBand, prepare_analysis_curves, biquad_response,
    cascade_biquads, compute_metrics,
)


def rescue_full_band_peak(inp, profile, plan, bands, *, target_kind):
    freqs=np.asarray(plan.freqs_hz,float)
    before_after=np.asarray(plan.mag_pred_db,float)
    goal=np.asarray(plan.target_db,float)
    bands=tuple(bands)
    if (target_kind!="Flat" or plan.status!="PREVIEW_READY"
            or len(bands)!=int(profile.max_filters) or len(bands)<2
            or freqs.size<80 or not np.isfinite(before_after).all()):
        return bands,before_after,()
    data=prepare_analysis_curves(inp,profile)
    if not np.allclose(data.grid_hz,freqs,rtol=1e-9,atol=1e-8):
        return bands,before_after,()
    w=np.asarray(data.weights,float)
    residual=before_after-goal
    trusted=((freqs>=profile.f_min_hz)&(freqs<=profile.f_max_hz)
             &(data.quality>=.80)&(data.reliability>=.70)
             &(~data.deep_null_mask)&(w>1e-5))
    peaks,_=find_peaks(residual,prominence=1.5,height=3.5)
    peaks=[int(i) for i in peaks if trusted[i] and
           not any(b.type=="P" and
                   abs(np.log2(freqs[i]/b.f_hz))<.12 for b in bands)]
    if not peaks:
        return bands,before_after,()
    peaks=sorted(peaks,key=lambda i:-residual[i])[:3]
    old=compute_metrics(data,goal,before_after,bands)
    protected=trusted&(residual<=-1.5)
    db_remove=[20*np.log10(np.maximum(np.abs(biquad_response(
        freqs,b,data.sample_rate)),1e-15)) for b in bands]
    best=None
    for i in peaks:
        center=float(freqs[i])
        near=(abs(np.log2(freqs/center))<=.16)&trusted
        if near.sum()<5:continue
        high=float(np.max(residual[near]))
        if high<3.5:continue
        for j,existing in enumerate(bands):
            if existing.type!="P":continue
            cleared=before_after-db_remove[j]
            for factor in (.985,1.,1.015):
                fc=center*factor
                if not profile.f_min_hz<fc<profile.f_max_hz:continue
                for q in (6.,8.,10.,12.,16.):
                    if q>profile.max_resonance_q:continue
                    for gain in (-3.,-4.,-5.,-6.,-7.,-8.,-9.):
                        if gain<profile.max_cut_db:continue
                        band=AutoEQBand("P",fc,float(gain),q)
                        new_db=20*np.log10(np.maximum(np.abs(
                            biquad_response(freqs,band,data.sample_rate)),1e-15))
                        pred=cleared+new_db
                        res=pred-goal
                        wrms=float(np.sqrt(np.dot(w,res*res)/max(float(w.sum()),1e-12)))
                        if wrms>old.weighted_rms_db-.04:continue
                        proposal=bands[:j]+(band,)+bands[j+1:]
                        m=compute_metrics(data,goal,pred,proposal)
                        if (m.p90_abs_error_db>old.p90_abs_error_db+.20 or
                                m.worst_abs_error_db>old.worst_abs_error_db+.16):
                            continue
                        if np.any(protected) and np.min(
                                (pred-before_after)[protected])<-.75:
                            continue
                        center_after=float(res[i])
                        new_peak=float(np.max(res[near]))
                        if (residual[i]-center_after<3. or
                                abs(center_after)>1.6 or
                                new_peak>high-1.5):
                            continue
                        rank=(wrms+.13*max(0.,new_peak)+
                              .012*abs(center_after)+.004*max(q-12.,0.),
                              wrms,new_peak,j,fc,q,gain)
                        if best is None or rank<best[0]:
                            best=(rank,proposal,i)
    if best is None:return bands,before_after,()
    final=best[1]
    old_eq=cascade_biquads(freqs,bands,data.sample_rate)
    new_eq=cascade_biquads(freqs,final,data.sample_rate)
    source_db=before_after-20*np.log10(np.maximum(np.abs(old_eq),1e-15))
    updated=source_db+20*np.log10(np.maximum(np.abs(new_eq),1e-15))
    i=best[2]
    warning=(f"PEAK_CUT_RESCUE {freqs[i]:.0f} Hz: "
             f"{residual[i]:+.2f} -> {updated[i]-goal[i]:+.2f} dB; "
             "1 PEQ replaced, DSP untouched")
    return final,updated,(warning,)
