# -*- coding: utf-8 -*-
"""Isolated RemiX Tune AEQ-U1.2-R2.4 adapter for V8.13 three-tool GUI.

This does NOT import/use the provisional V8.13 auto_peq algorithm.
Numeric design is delegated to the original RemiX Tune unified engine.
Data are supplied by the read-only Smaart TRF observer (T1, T2 or SUM).
No audio playback, no Smaart API control, no DSP write.
"""
from __future__ import annotations
from dataclasses import dataclass,replace
from functools import lru_cache
from copy import deepcopy
import numpy as np
from .autoeq_engine import (AutoEQInput,AutoEQProfile,
                                            design_unified_autoeq,AutoEQBand,
                                            cascade_biquads,prepare_analysis_curves,
                                            shared_autoeq_request_cache)
from .peak_rescue import rescue_full_band_peak
from .spacing import enforce_peq_spacing,close_pairs,MIN_SPACING_OCT
from .q_policy import safely_fill_residual_peaks,q_in_bounds

@dataclass(frozen=True)
class PEQ:
    freq_hz:float
    gain_db:float
    q:float

@dataclass(frozen=True)
class RemixEQResult:
    hz:np.ndarray
    before_db:np.ndarray
    after_db:np.ndarray
    target_db:np.ndarray
    peqs:tuple[PEQ,...]
    rms_before:float
    rms_after:float
    status:str
    fs:int
    source:str
    warnings:tuple[str,...]
    boost_limit_db:float=0.
    cut_limit_db:float=0.
    limits_auto:bool=False
    filter_limit:int=0
    filters_auto:bool=False

def target_anchors(kind:str,lo:float,hi:float):
    if kind=="Flat":
        return np.array([lo,hi],float),np.array([0.,0.])
    if kind=="House":
        base=((20.,3.),(80.,3.),(150.,1.5),(1000.,0.),(8000.,-1.),(20000.,-2.))
    elif kind=="Tilt":
        base=((20.,3.),(1000.,0.),(20000.,-3.))
    else:
        raise ValueError("Target must be Flat, House or Tilt")
    f0=np.array([a for a,_ in base],float)
    g0=np.array([b for _,b in base],float)
    result=np.array([lo,*[v for v in f0 if lo<v<hi],hi],float)
    return result,np.interp(np.log2(result),np.log2(f0),g0)

def design_remix_eq(hz,h,coherence,*,fs:int,target:str="Flat",
                    filters:int=8,lf:float=60.,hf:float=12000.,
                    boost:float=2.,cut:float=-9.,source:str="Trace"):
    if type(fs) is not int or fs not in (44100,48000,88200,96000,192000):
        raise ValueError("Fs phải được xác nhận")
    if type(filters) is not int or not 1<=filters<=12:
        raise ValueError("PEQ limit 1–12")
    if not (20<=float(lf)<float(hf)<=min(20000,fs*.49)):
        raise ValueError("Invalid LF/HF/Nyquist")
    if not 0<=float(boost)<=6 or not -12<=float(cut)<=-.1:
        raise ValueError("Unsafe cut/boost limits")
    freq=np.asarray(hz,dtype=float)
    complex_tf=np.asarray(h,dtype=np.complex128)
    quality=np.asarray(coherence,dtype=float)
    if (freq.ndim!=1 or len(freq)<32 or complex_tf.shape!=freq.shape
        or quality.shape!=freq.shape or np.any(np.diff(freq)<=0)
        or not np.isfinite(freq).all() or not np.isfinite(complex_tf).all()
        or not np.isfinite(quality).all() or np.any(quality<0)
        or np.any(quality>1) or freq[-1]>fs*.501):
        raise ValueError("Invalid or incompatible Smaart TF")
    # V8.135: coherence is diagnostic metadata, not an Auto EQ design gate.
    # Only real TF data and the requested working range decide which bins are
    # analysed. The solver receives neutral confidence so no downstream
    # coherence/local-support rule can silently reject an otherwise valid TF.
    analysis=(freq>=lf)&(freq<=hf)&(np.abs(complex_tf)>1e-12)
    if int(analysis.sum())<24:
        raise ValueError("Not enough TF bins in LF-HF")
    low_coherence=analysis&(quality<.60)
    reference_warnings=()
    if np.any(low_coherence):
        reference_warnings=(
            f"Coherence tham khảo: {100*low_coherence.sum()/analysis.sum():.0f}% "
            "dải LF-HF dưới 0.60; Auto EQ vẫn dùng toàn bộ dữ liệu TF",
        )
    level=float(np.median(20*np.log10(np.maximum(np.abs(complex_tf[analysis]),1e-15))))
    normalized=complex_tf*10**(-level/20.)
    t_freq,t_db=target_anchors(target,lf,hf)
    input_=AutoEQInput(
        freqs_hz=freq,h_corr=normalized,quality=np.ones_like(quality),
        quality_kind="coherence",sample_rate=float(fs),
        measurement_kind="stored_tf",target_freqs_hz=t_freq,
        target_db=t_db,smoothing_bpo=6.)
    profile=AutoEQProfile(
        f_min_hz=float(lf),f_max_hz=float(hf),max_filters=filters,
        max_peq=filters,max_boost_db=float(boost),max_cut_db=float(cut),
        max_low_shelf=0,max_high_shelf=0,
        min_q=3.0,max_q=8.0,max_resonance_q=8.0)
    result=design_unified_autoeq(input_,profile)
    bands=tuple(result.bands)
    if len(bands)>filters or any(b.type!="P" or b.gain_db>boost+1e-4
                                or b.gain_db<cut-1e-4 or
                                not (3.-1e-7<=float(b.q)<=8.+1e-7) for b in bands):
        raise ValueError("Original RemiX solver returned unsupported/out-of-bounds PEQ")
    base_eq=20*np.log10(np.maximum(np.abs(result.h_eq),1e-15))
    before=np.asarray(result.mag_pred_db,float)-base_eq
    bands,after,rescue_warnings=rescue_full_band_peak(
        input_,profile,result,bands,target_kind=target)
    # Final shared safety gate runs AFTER the residual peak pass: EQ,
    # marker, preview and export all receive the same spaced filters.
    bands,spaced_after,spacing_warnings=enforce_peq_spacing(
        input_,profile,bands,before,result.target_db,status=result.status)
    if spaced_after is not None:
        after=spaced_after
    bands,after,q_warnings=safely_fill_residual_peaks(
        input_,profile,bands,after,result.target_db,status=result.status)
    if close_pairs(bands,MIN_SPACING_OCT):
        raise ValueError("Spacing gate cannot export overlapping PEQ")
    if not q_in_bounds(bands):
        raise ValueError("AutoEQ Q outside 3-8 safety policy")
    eq=20*np.log10(np.maximum(np.abs(cascade_biquads(
        result.freqs_hz,bands,float(fs))),1e-15))
    if not np.allclose(after,before+eq,atol=1e-7,rtol=1e-7):
        raise ValueError("PEQ prediction not equal to exact reported cascade")
    control_f=np.asarray(result.freqs_hz,float)
    target_db=np.asarray(result.target_db,float)
    if not (len(control_f)==len(before)==len(after)==len(target_db)
            and np.isfinite(before).all() and np.isfinite(after).all()):
        raise ValueError("Original RemiX solver returned malformed Mag")
    peqs=tuple(PEQ(float(b.f_hz),float(b.gain_db),float(b.q)) for b in bands)
    status=str(result.status)
    if status!="PREVIEW_READY":
        peqs=()  # Fail-closed. No unsafe EQ proposal on other statuses.
    return RemixEQResult(control_f,before,after,target_db,peqs,
                         float(result.before.weighted_rms_db),
                         float(result.after.weighted_rms_db) if not (
                             rescue_warnings or spacing_warnings or q_warnings) else
                         float(np.sqrt(np.average(
                             (after-target_db)**2,
                             weights=prepare_analysis_curves(input_,profile).weights))),
                         status,fs,str(source),reference_warnings+tuple(result.warnings)+
                         rescue_warnings+spacing_warnings+q_warnings)


# V8.137: conservative-first search. Try familiar low-gain limits before
# widening cut and only then allowing more boost. The first safe plan wins;
# this avoids selecting +6 dB merely because it can improve RMS further.
# Four measured presets cover every successful plan in the 26 real Suite TRF
# survey. A larger 11-preset sweep added no success and made impossible traces
# wait 20-24 s, so keep the UI-bounded search small.
AUTO_LIMIT_CANDIDATES=((2.,-6.),(1.,-12.),(2.,-9.),(6.,-12.))
# Three representative budgets cover compact, normal and maximum correction.
# Testing every integer repeats the same expensive target-regression gates and
# measured up to 63.52 s on a real Suite trace; 4/8/12 preserves the full UI
# range while keeping the worker search bounded.
AUTO_PEQ_CANDIDATES=(4,8,12)
AUTO_PEQ_NEAR_BEST_DB=.05


def _design_with_auto_limits(hz,h,coherence,*,fs,target,filters,lf,hf,source):
    failures=[]
    for boost,cut in AUTO_LIMIT_CANDIDATES:
        try:
            result=design_remix_eq(
                hz,h,coherence,fs=fs,target=target,filters=filters,lf=lf,hf=hf,
                boost=boost,cut=cut,source=source)
        except ValueError as exc:
            failures.append(str(exc))
            continue
        if result.status=="NO_EQ_NEEDED" or result.peqs:
            note=(f"AUTO LIMITS: Boost +{boost:.1f} dB / Cut {cut:.1f} dB",)
            return replace(result,boost_limit_db=float(boost),cut_limit_db=float(cut),
                           limits_auto=True,filter_limit=int(filters),
                           warnings=result.warnings+note)
        failures.append("No approved PEQ")
    last=failures[-1] if failures else "no candidate"
    raise ValueError(f"Auto limits exhausted: {last}")


def _design_with_manual_limits(hz,h,coherence,*,fs,target,filters,lf,hf,
                               source,boost,cut):
    result=design_remix_eq(
        hz,h,coherence,fs=fs,target=target,filters=filters,lf=lf,hf=hf,
        boost=float(boost),cut=float(cut),source=source)
    return replace(result,boost_limit_db=float(boost),cut_limit_db=float(cut),
                   limits_auto=False,filter_limit=int(filters))


def _design_remix_eq_auto_limits_original(hz,h,coherence,*,fs:int,target:str="Flat",
                                filters:int=8,lf:float=60.,hf:float=12000.,
                                source:str="Trace",boost:float|None=None,
                                cut:float|None=None):
    """Choose safe PEQ count and Boost/Cut limits for one immutable TF.

    ``filters=0`` means AUTO. Select the smallest budget within 0.05 dB WRMS
    of the flattest safe plan. All solver/spacing/Q invariants remain intact.
    """
    manual=(boost is not None or cut is not None)
    if manual and (boost is None or cut is None):
        raise ValueError("Manual Boost/Cut must be supplied together")
    if manual and not (0.<=float(boost)<=6. and -12.<=float(cut)<0.):
        raise ValueError("Manual Boost/Cut outside supported range")
    design=(_design_with_manual_limits if manual else _design_with_auto_limits)
    extra=({"boost":float(boost),"cut":float(cut)} if manual else {})
    if filters:
        if type(filters) is not int or not 1<=filters<=12:
            raise ValueError("PEQ limit must be AUTO or 1–12")
        return design(
            hz,h,coherence,fs=fs,target=target,filters=filters,lf=lf,hf=hf,
            source=source,**extra)
    plans=[]
    failures=[]
    for count in AUTO_PEQ_CANDIDATES:
        try:
            plans.append(design(
                hz,h,coherence,fs=fs,target=target,filters=count,lf=lf,hf=hf,
                source=source,**extra))
        except ValueError as exc:
            failures.append(str(exc))
            if count==8 and plans:
                break
    if plans:
        best_rms=min(float(p.rms_after) for p in plans)
        chosen=min((p for p in plans
                    if float(p.rms_after)<=best_rms+AUTO_PEQ_NEAR_BEST_DB),
                   key=lambda p:(p.filter_limit,float(p.rms_after)))
        note=(f"AUTO PEQ: tối đa {chosen.filter_limit}, tạo {len(chosen.peqs)}; "
              f"WRMS cách tốt nhất {float(chosen.rms_after)-best_rms:+.2f} dB",)
        return replace(chosen,filters_auto=True,warnings=chosen.warnings+note)
    last=failures[-1] if failures else "no candidate"
    raise ValueError(f"Auto PEQ exhausted: {last}")


def _static_array_snapshot(value):
    """Immutable value snapshot; no stale TRF object pointers ever cached."""
    try:
        a=np.asarray(value)
        if a.ndim!=1 or a.dtype.kind not in "fciub":
            return None
        return (a.dtype.str,tuple(a.shape),np.ascontiguousarray(a).tobytes())
    except (TypeError,ValueError):
        return None


# QA instrumentation may replace solver internals. A result computed with
# one implementation must NEVER be served to another (also covers hot reload).
_R55_PRISTINE_DESIGN=(
    design_remix_eq,_design_with_auto_limits,_design_with_manual_limits,
    tuple(AUTO_LIMIT_CANDIDATES),tuple(AUTO_PEQ_CANDIDATES))


def _r55_design_implementation_unchanged():
    return (design_remix_eq is _R55_PRISTINE_DESIGN[0] and
            _design_with_auto_limits is _R55_PRISTINE_DESIGN[1] and
            _design_with_manual_limits is _R55_PRISTINE_DESIGN[2] and
            tuple(AUTO_LIMIT_CANDIDATES)==_R55_PRISTINE_DESIGN[3] and
            tuple(AUTO_PEQ_CANDIDATES)==_R55_PRISTINE_DESIGN[4])


@lru_cache(maxsize=8)
def _exact_cached_auto_design(snapshots, fs, target, filters, lf, hf, source,
                              boost, cut):
    """Only successful full solver results cache; all guards run on miss.

    Every numeric source byte + all scalar parameters are in the cache key.
    Full numpy outputs are deep-copied before returning to GUI consumers.
    """
    values=[np.frombuffer(raw,dtype=np.dtype(dtype)).reshape(shape)
            for dtype,shape,raw in snapshots]
    with shared_autoeq_request_cache():
        return _design_remix_eq_auto_limits_original(
            *values,fs=fs,target=target,filters=filters,lf=lf,hf=hf,
            source=source,boost=boost,cut=cut)


def design_remix_eq_auto_limits(hz,h,coherence,*,fs:int,target:str="Flat",
                                filters:int=8,lf:float=60.,hf:float=12000.,
                                source:str="Trace",boost:float|None=None,
                                cut:float|None=None):
    """Exact deterministic static-result cache, never an export entitlement.

    Changed TF bytes, Fs, target, ROI, limits, filter budget, or source
    always cause a new full solver run. Errors are not cached. Manual
    output edits cannot mutate cached numpy arrays.
    """
    snapshots=tuple(_static_array_snapshot(v) for v in (hz,h,coherence))
    if any(s is None for s in snapshots) or not _r55_design_implementation_unchanged():
        with shared_autoeq_request_cache():
            return _design_remix_eq_auto_limits_original(
                hz,h,coherence,fs=fs,target=target,filters=filters,lf=lf,hf=hf,
                source=source,boost=boost,cut=cut)
    answer=_exact_cached_auto_design(snapshots,fs,target,filters,lf,hf,
                                     source,boost,cut)
    return deepcopy(answer)
