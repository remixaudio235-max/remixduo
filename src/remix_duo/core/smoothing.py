"""Independent fractional-octave *display* smoothing for model SUM TF.

Physical complex SUM and AutoAlign solver remain untouched. No Smaart
algorithm or MTW parity is claimed. Angles are averaged as unit phasors;
never arithmetically average wrapped degrees.
"""
from __future__ import annotations
import numpy as np

SMOOTH_OPTIONS=(("Off",0.),("1/48 Oct",1/48),("1/24 Oct",1/24),
                ("1/12 Oct",1/12),("1/6 Oct",1/6),("1/3 Oct",1/3))

def smooth_log_octaves(f,values,width_oct,weights=None):
    """Gaussian log-frequency smoothing of a real-valued display series."""
    f=np.asarray(f,dtype=np.float64)
    values=np.asarray(values,dtype=np.float64)
    if f.ndim!=1 or values.shape!=f.shape or np.any(f<=0) or np.any(np.diff(f)<=0):
        raise ValueError("Invalid frequency or smoothing arrays")
    if not width_oct:return values.copy()
    sigma=float(width_oct)/2.354820045
    if not (0<sigma<=1):raise ValueError("Invalid smoothing octave fraction")
    x=np.log2(f)
    out=np.full_like(values,np.nan)
    if weights is None: weights=np.ones_like(values)
    else: weights=np.asarray(weights,dtype=float)
    for i,at in enumerate(x):
        lo=np.searchsorted(x,at-3*sigma,side="left")
        hi=np.searchsorted(x,at+3*sigma,side="right")
        d=(x[lo:hi]-at)/sigma
        w=np.exp(-.5*d*d)*np.maximum(weights[lo:hi],0)
        good=np.isfinite(values[lo:hi])&np.isfinite(w)&(w>0)
        if np.any(good):
            out[i]=np.dot(w[good],values[lo:hi][good])/w[good].sum()
    return out

def smooth_phase_unit_phasor(f,h,coherence,width_oct,coh_gate=.60,
                             min_resultant=.18):
    """Coherence-weighted circular smoothing, with unreliable output masked.

    Weight bins by coherence^2; low coherence does not rotate high-quality
    neighboring phases. Resultant length detects cancellation in strong
    oscillatory/notch regions and avoids reporting arbitrary angles.
    """
    f=np.asarray(f,dtype=float)
    h=np.asarray(h,dtype=np.complex128)
    coh=np.asarray(coherence,dtype=float)
    if h.shape!=f.shape or coh.shape!=f.shape:
        raise ValueError("Complex phase shape mismatch")
    base=np.rad2deg(np.angle(h))
    good=np.isfinite(coh)&(coh>=coh_gate)&np.isfinite(h.real)&np.isfinite(h.imag)&(np.abs(h)>1e-12)
    if not width_oct:
        return base.copy(),good, np.where(good,1.,0.)
    sigma=float(width_oct)/2.354820045
    if not (0<sigma<=1):raise ValueError("Invalid phase smoothing octave fraction")
    x=np.log2(f)
    with np.errstate(invalid="ignore"):  # V8.115: NaN no-data bins are masked
        unit=h/np.maximum(np.abs(h),1e-15)
    out=np.full(f.shape,np.nan)
    mask=np.zeros(f.shape,dtype=bool)
    concentration=np.zeros(f.shape,dtype=float)
    for i,at in enumerate(x):
        if not good[i]:
            continue
        lo=np.searchsorted(x,at-3*sigma,side="left")
        hi=np.searchsorted(x,at+3*sigma,side="right")
        region=good[lo:hi]
        if not np.any(region):continue
        d=(x[lo:hi]-at)/sigma
        w=np.exp(-.5*d*d)*np.square(np.clip(coh[lo:hi],0,1))
        w[~region]=0.
        denom=float(w.sum())
        if denom<=1e-15:continue
        z=np.dot(w,unit[lo:hi])/denom
        strength=float(abs(z))
        concentration[i]=strength
        if strength < min_resultant:continue
        out[i]=np.rad2deg(np.angle(z))
        mask[i]=True
    out[~mask]=base[~mask]  # hidden by phase_valid; preserve finite source values
    return out,mask,concentration
