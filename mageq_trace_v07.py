# -*- coding: utf-8 -*-
"""A *new* MagEq curve for one Smaart source trace, never a mutation.

V0.7 MagEq is a read-only overlay trace. It is NOT injected into Smaart's
Trace List and it is NEVER stored in, or applied to, the source .trf.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import numpy as np
from tf_display_smoothing import smooth_log_octaves
from engines.remix_autoeq_unified import AutoEQBand,cascade_biquads

@dataclass(frozen=True)
class MagEqTrace:
    name:str
    source_name:str
    source_index:int
    source_identity:str
    revision:int
    fs:int
    freq_hz:np.ndarray
    original_mag_db:np.ndarray
    mageq_mag_db:np.ndarray
    coherence:np.ndarray
    bands:tuple[AutoEQBand,...]

def _frozen(a,dtype):
    result=np.array(a,dtype=dtype,copy=True)
    result.setflags(write=False)
    return result

def create_mageq_trace(freq,h,coherence,peqs,*,fs,source_index,source_name,revision,allow_bypass=False):
    """Produce exactly one new MagEq view without altering original arrays.

    The same RemiX Tune PEQ biquads as the AutoEQ solver are evaluated against
    the original stored complex H. Do not overwrite or regenerate H.
    """
    if source_index not in (0,1):
        raise ValueError("Choose exactly one original Smaart trace: T1 or T2; SUM HOLD")
    if type(fs) is not int or fs not in (44100,48000,88200,96000,192000):
        raise ValueError("Unconfirmed sample rate")
    freq=np.asarray(freq,float)
    H=np.asarray(h,complex)
    coh=np.asarray(coherence,float)
    if (freq.ndim!=1 or len(freq)<80 or freq.shape!=H.shape or
            freq.shape!=coh.shape or not np.isfinite(freq).all() or
            not np.isfinite(H).all() or not np.isfinite(coh).all() or
            np.any(np.diff(freq)<=0) or np.any(coh<0) or np.any(coh>1)):
        raise ValueError("Invalid original TF (frequency/H/coherence)")
    bands=tuple(AutoEQBand("P",float(p.freq_hz),float(p.gain_db),float(p.q))
                for p in peqs)
    if not source_name or len(bands)>12 or (not bands and not allow_bypass):
        raise ValueError("MagEq requires a named source and valid PEQ (or explicit BYPASS)")
    if any(not (20<=b.f_hz<fs*.49 and -12<=b.gain_db<=6 and
                .3<=b.q<=16 and np.isfinite([b.f_hz,b.gain_db,b.q]).all())
           for b in bands):
        raise ValueError("Out-of-range MagEq PEQ band")
    # Identifier includes full original TF; a different measurement from a
    # file bearing the SAME name will create a different MagEq revision.
    sha=hashlib.sha256()
    for arr in (np.asarray(freq,dtype="<f8"),
                np.asarray(H.real,dtype="<f8"),
                np.asarray(H.imag,dtype="<f8"),
                np.asarray(coh,dtype="<f8")):
        sha.update(arr.tobytes())
    identity=sha.hexdigest()
    mag=smooth_log_octaves(freq,20*np.log10(np.maximum(np.abs(H),1e-15)),1/6)
    # Downsample after smoothing so no source bin is silently redefined.
    if len(freq)>1600:
        idx=np.unique(np.rint(np.linspace(0,len(freq)-1,1600)).astype(int))
        out_freq=freq[idx]
        out_mag=mag[idx]
        out_coh=coh[idx]
    else:
        out_freq=freq
        out_mag=mag
        out_coh=coh
    response=(cascade_biquads(out_freq,bands,fs) if bands
              else np.ones(out_freq.shape,dtype=complex))
    correction=20*np.log10(np.maximum(np.abs(response),1e-15))
    if not np.isfinite(correction).all() or not np.isfinite(out_mag).all():
        raise ValueError("Invalid MagEq correction")
    return MagEqTrace(
        name=f"MagEq [{source_name}]",
        source_name=str(source_name),
        source_index=int(source_index),
        source_identity=identity,
        revision=int(revision),
        fs=fs,
        freq_hz=_frozen(out_freq,float),
        original_mag_db=_frozen(out_mag,float),
        mageq_mag_db=_frozen(out_mag+correction,float),
        coherence=_frozen(out_coh,float),
        bands=bands,
    )
