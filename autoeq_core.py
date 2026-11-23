# -*- coding: utf-8 -*-
"""Isolated read-only TF -> RemiX AutoEQ. No dependency on AutoPhase GUI.

Source snapshot: V8.8 TRF parser + RemiX Tune AEQ-U1.2-R2.4 solver.
An EQ result is a proposed offline correction, NEVER a Smaart/DSP write.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import sys
import numpy as np

ENGINE = Path(__file__).resolve().parent / "engines"
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))
from remix_autoeq_unified import (AutoEQInput, AutoEQProfile, AutoEQBand,
                                  cascade_biquads, design_unified_autoeq)
from smaart_format_adapter import read_stored_tf,read_target_crv,read_ascii_tf
from trf_core import read_trf  # backward-compatible public import for existing QA

FS_ALLOWED=(44100,48000,88200,96000,192000)
MAX_FILE_BYTES=32*1024*1024

@dataclass(frozen=True)
class EQConfig:
    sample_rate:int=48000
    lf:float=60.0
    hf:float=12000.0
    max_filters:int=12
    max_boost_db:float=2.0
    max_cut_db:float=-9.0
    target:str="Flat"
    target_curve_path:str=""
    source_trace:str=""
    def validate(self):
        if type(self.sample_rate) is not int or self.sample_rate not in FS_ALLOWED:
            raise ValueError("Sample rate must be operator-confirmed 44.1/48/88.2/96/192 kHz")
        if not (20.0<=float(self.lf)<float(self.hf)<=min(20000,self.sample_rate*.49)):
            raise ValueError("Invalid LF/HF or Nyquist")
        if type(self.max_filters) is not int or not 1<=self.max_filters<=12:
            raise ValueError("Maximum 1–12 EQ bands")
        if not (0<=float(self.max_boost_db)<=6):
            raise ValueError("Boost safety bound must be 0–6 dB")
        if not (-12<=float(self.max_cut_db)<=-0.1):
            raise ValueError("Cut bound must be -12 to -0.1 dB")
        if self.target not in ("Flat","House","Tilt","Smaart CRV"):
            raise ValueError("Unknown target curve")
        if self.target=="Smaart CRV":
            if not self.target_curve_path or Path(self.target_curve_path).suffix.lower()!=".crv":
                raise ValueError("Choose a Smaart TF target .crv file")

def _target(config:EQConfig):
    lo=float(config.lf); hi=float(config.hf)
    if config.target=="Smaart CRV":
        f,db=read_target_crv(config.target_curve_path)
        inner=f[(f>lo)&(f<hi)]
        res=np.array([lo,*inner,hi],float)
        return res,np.interp(np.log2(res),np.log2(f),db)
    if config.target=="Flat":
        return np.array([lo,hi]),np.zeros(2)
    anchors=[(20.0,3.0),(80.0,3.0),(150.0,1.5),(1000.0,0.0),
             (8000.0,-1.0),(20000.0,-2.0)] if config.target=="House" else [
             (20.0,3.0),(1000.0,0.0),(20000.0,-3.0)]
    pts=np.array([x for x,_ in anchors])
    values=np.array([y for _,y in anchors])
    internal=[float(x) for x in pts if lo<float(x)<hi]
    freqs=np.array([lo,*internal,hi],float)
    targets=np.interp(np.log2(freqs),np.log2(pts),values)
    return freqs,targets

def fingerprint(path:Path):
    p=Path(path).resolve()
    if p.suffix.lower() not in (".trf",".txt",".crv"):
        raise ValueError("Only stored .trf/.txt and .crv targets are allowed")
    st=p.stat()
    minimum=750 if p.suffix.lower()==".trf" else 16
    if st.st_size<minimum or st.st_size>MAX_FILE_BYTES:
        raise ValueError("Unexpected measurement/target file size")
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    return f"{st.st_size}:{st.st_mtime_ns}:{digest}"

@dataclass(frozen=True)
class EQResult:
    path:Path
    revision:str
    config:EQConfig
    status:str
    frequencies:np.ndarray
    before_db:np.ndarray
    after_db:np.ndarray
    target_db:np.ndarray
    bands:tuple[AutoEQBand,...]
    before_wrms_db:float
    after_wrms_db:float
    level_offset_db:float
    warnings:tuple[str,...]
    original_coherence:np.ndarray
    target_revision:str=""

def design(path, config:EQConfig) -> EQResult:
    config.validate()
    path=Path(path).resolve()
    revision=fingerprint(path)
    target_revision=fingerprint(config.target_curve_path) if config.target=="Smaart CRV" else ""
    trace=(read_trf(path) if path.suffix.lower()==".trf" else
           read_ascii_tf(path,trace_key=config.source_trace or None))
    if revision!=fingerprint(path):
        raise ValueError("Source TF changed during read")
    f=np.asarray(trace.hz,float)
    h=np.asarray(trace.h,complex)
    c=np.asarray(trace.coherence,float)
    if (len(f)<32 or f[-1]>config.sample_rate*.501 or
            not np.isfinite(h.real).all() or not np.isfinite(h.imag).all()):
        raise ValueError("TF data invalid for selected sample rate")
    valid=(f>=config.lf)&(f<=config.hf)&(c>=.60)&(np.abs(h)>1.e-12)
    if int(valid.sum())<24:
        raise ValueError("Fewer than 24 coherence-qualified bins (>=0.60)")
    offset=float(np.median(20*np.log10(np.maximum(np.abs(h[valid]),1.e-15))))
    norm=h*10**(-offset/20.)
    t_f,t_db=_target(config)
    inp=AutoEQInput(freqs_hz=f,h_corr=norm,quality=c,
                    quality_kind="coherence",sample_rate=float(config.sample_rate),
                    measurement_kind="stored_tf",target_freqs_hz=t_f,
                    target_db=t_db,smoothing_bpo=6.)
    p=AutoEQProfile(f_min_hz=float(config.lf),f_max_hz=float(config.hf),
                    max_filters=config.max_filters,max_peq=config.max_filters,
                    max_boost_db=float(config.max_boost_db),
                    max_cut_db=float(config.max_cut_db))
    plan=design_unified_autoeq(inp,p)
    bandtuple=tuple(plan.bands)
    if len(bandtuple)>config.max_filters:
        raise RuntimeError("EQ engine exceeded user filter budget")
    if any(b.gain_db>config.max_boost_db+1e-4 or
           b.gain_db<config.max_cut_db-1e-4 for b in bandtuple):
        raise RuntimeError("EQ engine produced out-of-bounds band")
    if revision!=fingerprint(path):
        raise ValueError("Source TF changed during calculation")
    if target_revision and fingerprint(config.target_curve_path)!=target_revision:
        raise ValueError("Smaart target CRV changed during calculation")
    # GUI must use the solver's smoothed Mag authority, NOT raw complex H.
    # Unsmoothing via h_pred/h_eq creates a false before/after mismatch.
    eq_db=20*np.log10(np.maximum(np.abs(plan.h_eq),1e-15))
    before_db=np.asarray(plan.mag_pred_db,float)-eq_db
    # Predictive plan after follows the actual biquad response; never conflate
    # absolute display Y offset with physical EQ gain.
    return EQResult(path,revision,config,str(plan.status),
                    np.asarray(plan.freqs_hz).copy(),before_db,
                    np.asarray(plan.mag_pred_db).copy(),
                    np.asarray(plan.target_db).copy(),bandtuple,
                    float(plan.before.weighted_rms_db),
                    float(plan.after.weighted_rms_db),offset,
                    tuple(plan.warnings),c.copy(),target_revision)

def preview_edit(result:EQResult,bands:tuple[AutoEQBand,...]):
    """Recompute post-EQ curve from manual marker edits; not a safety-certified plan."""
    if len(bands)>result.config.max_filters:
        raise ValueError("Manual edit exceeds filter limit")
    for b in bands:
        if (b.type not in ("P","LS","HS") or
            not result.config.lf<=b.f_hz<=result.config.hf or
            not result.config.max_cut_db<=b.gain_db<=result.config.max_boost_db or
            not .3<=b.q<=16 or not np.isfinite([b.f_hz,b.gain_db,b.q]).all()):
            raise ValueError("Manual EQ band outside correction limits")
    heq=cascade_biquads(result.frequencies,bands,result.config.sample_rate)
    return result.before_db+20*np.log10(np.maximum(np.abs(heq),1e-15))

def text_export(result:EQResult,bands:tuple[AutoEQBand,...]):
    """Human-readable proposed coefficients, explicitly NOT a device preset."""
    if result.status!="PREVIEW_READY":
        raise ValueError("No safe engine-approved EQ plan to export")
    _=preview_edit(result,bands)
    if result.target_revision and fingerprint(result.config.target_curve_path)!=result.target_revision:
        raise ValueError("Target CRV changed; recompute AutoEQ")
    rows=[
       "# RemiX Signal Auto EQ — OFFLINE PREVIEW / MANUAL SETTINGS",
       "# NOT A Smaart preset. NOT a DSP firmware/preset file.",
       "# Manual marker edits require independent acoustic/do-no-harm validation.",
       "# Source: "+str(result.path),
       "# Source revision SHA256: "+result.revision.split(":")[-1],
       f"# Fs: {result.config.sample_rate} Hz",
       f"# Correction LF/HF: {result.config.lf:.1f}/{result.config.hf:.1f} Hz",
       f"# Target: {result.config.target}",
       "# No auto-apply, no hardware writes, no Generator.",
       "EQ#,TYPE,Hz,dB,Q"
    ]
    rows += [f"{i},{b.type},{b.f_hz:.2f},{b.gain_db:+.3f},{b.q:.3f}"
             for i,b in enumerate(bands,1)]
    return "\n".join(rows)+"\n"
