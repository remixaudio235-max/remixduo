"""V8.50 production-safe PEQ spacing on a logarithmic frequency axis.

Enforces >= 1/4 octave between EVERY PEQ center, including after V8.49
residual rescue. Merge clusters with an exact biquad fit to the same
weighted TF/target. Never manipulate Smaart/audio/DSP.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from scipy.optimize import minimize_scalar
from .autoeq_engine import (
    AutoEQBand, biquad_response, cascade_biquads,
    prepare_analysis_curves, compute_metrics,
)

MIN_SPACING_OCT = .25


def _hz(b):
    """Accept native solver bands and the public GUI/export PEQ structure."""
    return float(b.f_hz if hasattr(b,"f_hz") else b.freq_hz)


def close_pairs(bands, minimum_oct=MIN_SPACING_OCT):
    """Return sorted frequency pairs that violate the hard center spacing."""
    ordered=sorted(bands,key=_hz)
    return tuple((a,b) for a,b in zip(ordered,ordered[1:])
                 if math.log2(_hz(b)/_hz(a))<minimum_oct-1e-8)


def _mag_db(freqs,bands,fs):
    return 20*np.log10(np.maximum(np.abs(cascade_biquads(
        freqs,bands,fs)),1e-15))


def _groups(bands,minimum_oct):
    ordered=sorted(bands,key=lambda b:float(b.f_hz))
    groups=[]
    group=[ordered[0]]
    for b in ordered[1:]:
        if math.log2(float(b.f_hz)/float(group[-1].f_hz))<minimum_oct-1e-8:
            group.append(b)
        else:
            groups.append(tuple(group))
            group=[b]
    groups.append(tuple(group))
    return groups


def _combine_one(freqs,src_db,target,weights,original,others,group,profile,
                 minimum_oct):
    """Replace one frequency cluster by a single exact PEQ, with safeguards."""
    fs=profile.sample_rate if hasattr(profile,"sample_rate") else None
    if fs is None:
        raise ValueError("sample_rate required for spacing fit")
    base=src_db+_mag_db(freqs,others,fs)
    group_f=[float(b.f_hz) for b in group]
    f0,f1=min(group_f),max(group_f)
    gmin=min(float(profile.max_cut_db),-.1)
    gmax=float(profile.max_boost_db)
    # Cluster centers, not arbitrary broad search: preserve the measured
    # feature location and do not replace it with an unrelated peak.
    f_candidates=list(group_f)
    f_candidates += [float(np.exp(np.mean(np.log(group_f)))),
                     float(np.exp(np.average(np.log(group_f),
                          weights=[max(.1,abs(b.gain_db)) for b in group])))]
    f_candidates += list(np.geomspace(f0,f1,7))
    q_candidates=(2.,3.,4.,5.,6.,8.,10.,12.,16.)
    q_candidates+=tuple(float(b.q) for b in group)
    # Most clusters of same-sign cuts should remain cuts; don't turn
    # an overlapping cut cluster into a new boost.
    negative=all(b.gain_db<0 for b in group)
    positive=all(b.gain_db>0 for b in group)
    if negative:gmax=-.3
    if positive:gmin=.3
    if gmax<=gmin:return None
    active=np.asarray(weights)>1e-8
    if active.sum()<12:return None
    min_oct=minimum_oct
    best=None
    old_err=np.asarray(original,float)-target
    protect=(old_err < -2.) & active
    for fc in sorted(set(round(v,8) for v in f_candidates)):
        if not (profile.f_min_hz<=fc<=profile.f_max_hz):continue
        if any(abs(math.log2(fc/float(b.f_hz)))<min_oct-1e-8 for b in others):
            continue
        for q in sorted(set(round(v,5) for v in q_candidates)):
            if not (profile.min_q<=q<=profile.max_resonance_q):continue
            def trial(g):
                band=AutoEQBand("P",fc,float(g),q)
                y=base+20*np.log10(np.maximum(np.abs(
                    biquad_response(freqs,band,fs)),1e-15))
                return y,band
            def obj(g):
                y,_=trial(g)
                err=y-target
                # Weighted error + modest overshoot protection; avoid
                # flattening a peak by creating a new deep local dip.
                rms2=float(np.dot(weights,err*err)/max(float(weights.sum()),1e-12))
                harm=float(np.min((y-original)[protect])) if protect.any() else 0.
                penalty=1.2*max(0.,-harm-.60)**2
                return rms2+penalty
            try:
                optimum=minimize_scalar(obj,bounds=(gmin,gmax),
                    method="bounded",options={"xatol":.03,"maxiter":22})
                gain=float(optimum.x)
            except ValueError:
                continue
            y,band=trial(gain)
            rms=float(np.sqrt(np.dot(weights,(y-target)**2)/
                              max(float(weights.sum()),1e-12)))
            if protect.any() and np.min((y-original)[protect])<-.90:
                continue
            # High gain / very narrow candidate should not be selected
            # solely for a tiny global RMS advantage.
            rank=(rms+.012*max(0.,q-12.)+.0025*abs(gain),rms,
                  abs(math.log2(fc/np.exp(np.mean(np.log(group_f))))),fc,q)
            if best is None or rank<best[0]:
                best=(rank,band,y)
    return best


def enforce_peq_spacing(inp,profile,bands,source_db,target_db,*,status,
                        minimum_oct=MIN_SPACING_OCT):
    """Resolve overlapping PEQ centers; return plan and diagnostic warnings.

    Max PEQ is an upper bound. If no safe merge can satisfy the minimum,
    fall back to a separated subset. No hidden overlapping filters.
    """
    bands=tuple(bands)
    src=np.asarray(source_db,float)
    target=np.asarray(target_db,float)
    if not bands or status!="PREVIEW_READY" or not close_pairs(bands,minimum_oct):
        return bands,None,()
    data=prepare_analysis_curves(inp,profile)
    freqs=np.asarray(data.grid_hz,float)
    if not (len(src)==len(freqs)==len(target)):
        raise ValueError("spacing grid/source mismatch")
    # Make a private, immutable-profile sample-rate holder for _combine_one.
    from types import SimpleNamespace
    solver=SimpleNamespace(**{key:getattr(profile,key) for key in (
        "min_q","max_resonance_q","max_cut_db","max_boost_db",
        "f_min_hz","f_max_hz")},sample_rate=float(inp.sample_rate))
    original=src+_mag_db(freqs,bands,float(inp.sample_rate))
    baseline_metrics=compute_metrics(data,target,original,bands)
    groups=_groups(bands,minimum_oct)
    resolved=tuple()
    collapsed=0
    for i,cluster in enumerate(groups):
        if len(cluster)==1:
            resolved+=cluster
            continue
        remaining=resolved+tuple(b for group in groups[i+1:] for b in group)
        trial=_combine_one(freqs,src,target,data.weights,original,
                           remaining,cluster,solver,minimum_oct)
        if trial is None:
            # Reject an unsafe fit. Keep one original peak in this group
            # that minimizes weighted residual after dropping siblings.
            candidate=None
            for b in cluster:
                pool=remaining+(b,)
                # Other, not-yet-merged groups can contain independent
                # close pairs; do not let their conflicts falsely block
                # every fallback candidate in THIS group.
                if any(abs(math.log2(_hz(b)/_hz(peer)))<
                       minimum_oct-1e-8 for peer in remaining):
                    continue
                pred=src+_mag_db(freqs,pool,float(inp.sample_rate))
                rms=float(np.sqrt(np.average((pred-target)**2,
                                             weights=data.weights)))
                if candidate is None or rms<candidate[0]:
                    candidate=(rms,b)
            if candidate is None:
                # Rare adversarial case: existing adjacent group may
                # conflict with all choices. Drop the entire group;
                # user must not receive a false "safe" preview.
                collapsed+=len(cluster)
                continue
            merged=candidate[1]
        else:
            merged=trial[1]
        resolved+=(merged,)
        collapsed+=len(cluster)-1
    # Final global proof, not merely group-local testing. Preserve user
    # limits and never publish invisible overlapping bands.
    if close_pairs(resolved,minimum_oct):
        raise ValueError("EQ spacing invariant broken")
    out=src+_mag_db(freqs,resolved,float(inp.sample_rate))
    if not np.isfinite(out).all():
        raise ValueError("nonfinite EQ spacing output")
    new_metrics=compute_metrics(data,target,out,resolved)
    # Fail closed instead of silently releasing widely spaced but
    # harmful EQ when an exotic trace cannot be merged safely.
    if (new_metrics.weighted_rms_db>baseline_metrics.weighted_rms_db+.20 or
            new_metrics.p90_abs_error_db>baseline_metrics.p90_abs_error_db+.35 or
            new_metrics.worst_abs_error_db>baseline_metrics.worst_abs_error_db+.50):
        raise ValueError("No safe 1/4-oct PEQ plan: unacceptable target regression")
    old_res=original-target
    near_null=(data.quality>=.6)&(data.reliability>=.6)&(old_res<=-1.5)
    if np.any(near_null) and np.min((out-original)[near_null])<-1.0:
        raise ValueError("No safe 1/4-oct PEQ plan: worsened nearby dip")
    if (len(resolved)>profile.max_filters or
            any(b.gain_db<profile.max_cut_db-1e-6 or
                b.gain_db>profile.max_boost_db+1e-6 for b in resolved)):
        raise ValueError("PEQ spacing violated max filters/gain limits")
    report=(f"PEQ_SPACING_1_4_OCT: merged {collapsed} overlapping "
            f"filter(s), {len(bands)} -> {len(resolved)} PEQ",)
    return resolved,out,report
