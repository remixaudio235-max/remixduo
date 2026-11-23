# -*- coding: utf-8 -*-
"""Strict read-only Smaart ASCII TF / Smaart target CRV adapter.

Interoperability based on public Smaart ASCII and CRV format examples
documented in Jamesits/eqx. Only imports; never writes Smaart or a DSP.
Reject missing coherence/phase rather than fabricating a valid complex TF.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import re
import numpy as np

MAX_BYTES=16*1024*1024

@dataclass(frozen=True)
class TFTable:
    name:str
    hz:np.ndarray
    h:np.ndarray
    coherence:np.ndarray
    source_format:str="smaart-ascii"

def _text(path):
    p=Path(path).resolve()
    if not p.is_file() or p.stat().st_size>MAX_BYTES or p.stat().st_size<16:
        raise ValueError("Missing/oversized Smaart text file")
    data=p.read_bytes()
    if b"\x00" in data:raise ValueError("Binary data is not Smaart ASCII/CRV")
    return data.decode("utf-8-sig",errors="strict")

def _float(cell,where):
    value=cell.strip()
    if not value or value=="*":return None
    try:x=float(value.replace(",","."))
    except ValueError:raise ValueError(f"{where}: invalid numeric cell")
    if not np.isfinite(x):raise ValueError(f"{where}: nonfinite numeric cell")
    return x

def read_ascii_tf(path,trace_key=None):
    text=_text(path)
    lines=text.splitlines()
    head=None
    for i,line in enumerate(lines):
        raw=line.lstrip("*; ").strip()
        if raw.lower().startswith("frequency (hz)\t"):
            head=i
            break
    if head is None:raise ValueError("Missing Smaart Frequency (Hz) header")
    fields=lines[head].lstrip("*; ").strip().split("\t")
    labels=[v.strip().lower() for v in fields]
    starts=[i for i,x in enumerate(labels) if x in ("magnitude (db)","level (db)")]
    if not starts:raise ValueError("Smaart ASCII needs Magnitude (dB)")
    names=lines[head-1].lstrip("*; ").split("\t") if head else []
    traces=[]
    for j,start in enumerate(starts):
        end=starts[j+1] if j+1<len(starts) else len(fields)
        group=labels[start:end]
        if group[0]!="magnitude (db)" or "phase (degrees)" not in group or "coherence" not in group:
            continue
        name=names[start].strip() if start<len(names) else f"Trace {j+1}"
        traces.append((name,start+group.index("phase (degrees)"),
                       start+group.index("coherence"),start))
    if not traces:raise ValueError("ASCII is not TF with Mag/Phase/Coherence")
    if trace_key is None:
        if len(traces)!=1:raise ValueError("Multi-trace ASCII requires trace selection by name/index")
        selected=traces[0]
    elif isinstance(trace_key,int):
        if trace_key<0 or trace_key>=len(traces):raise ValueError("Trace index invalid")
        selected=traces[trace_key]
    else:
        found=[row for row in traces if row[0].casefold()==str(trace_key).strip().casefold()]
        if len(found)!=1:raise ValueError("Trace name missing/ambiguous")
        selected=found[0]
    name,phase_col,coh_col,mag_col=selected
    freqs=[];Hs=[];cohs=[]
    for n,line in enumerate(lines[head+1:],head+2):
        if not line.strip() or line.lstrip().startswith(("*",";")):continue
        cells=line.split("\t")
        if max(phase_col,coh_col,mag_col)>=len(cells):
            raise ValueError(f"ASCII line {n}: too few columns")
        v=[_float(cells[k],f"line {n}") for k in (0,mag_col,phase_col,coh_col)]
        if any(z is None for z in v):continue
        f,db,deg,c=v
        if f<=0 or not 0<=c<=1:
            raise ValueError(f"ASCII line {n}: invalid frequency/coherence")
        freqs.append(f);Hs.append(10**(db/20)*np.exp(1j*np.deg2rad(deg)));cohs.append(c)
    if len(freqs)<32:raise ValueError("ASCII requires >=32 complete TF bins")
    ff=np.asarray(freqs,dtype=float)
    if not np.all(np.diff(ff)>0):raise ValueError("ASCII frequencies not strictly increasing")
    return TFTable(name,ff,np.asarray(Hs,complex),np.asarray(cohs,float))

def read_target_crv(path):
    """Smaart TF target .crv; returns Hz/dB, header read-only.

    Explicit offset in CRV is *not* silently applied. The EQ target is
    normalized around 1 kHz as a response *shape*, not an absolute SPL target.
    """
    txt=_text(path)
    header={}
    points={}
    for ln in txt.splitlines():
        s=ln.strip()
        if not s or s.startswith(("*",";")):continue
        if ":" in s and re.match(r"^[A-Za-z]+\s*:",s):
            k,v=s.split(":",1)
            header[k.strip().lower()]=v.strip()
            continue
        cells=s.split("\t")
        if len(cells)!=2:continue
        f=_float(cells[0],"crv frequency")
        db=_float(cells[1],"crv dB")
        if f is None or db is None or f<=0:continue
        if f in points:raise ValueError("Duplicate target frequency")
        points[f]=db
    if header.get("type","").upper()!="TF":
        raise ValueError("Only Smaart TF target .crv (Type: TF) supported")
    if len(points)<2:raise ValueError("Target CRV requires >=2 points")
    if len(points)>8192:raise ValueError("Target CRV too many points")
    f=np.array(sorted(points),float);db=np.array([points[x] for x in f],float)
    if f[0]<1 or f[-1]>200000:raise ValueError("Target frequency invalid")
    # Preserve shape, remove arbitrary absolute level offset so device
    # SPL target values do not create dangerous broadband boost.
    base=float(np.interp(np.log2(1000.),np.log2(f),db))
    return f,db-base

def read_stored_tf(path,trace_key=None):
    p=Path(path)
    if p.suffix.lower()==".trf":
        from trf_core import read_trf
        return read_trf(p)
    if p.suffix.lower()==".txt":
        return read_ascii_tf(p,trace_key=trace_key)
    raise ValueError("Only .trf or complete Smaart ASCII TF .txt accepted")

def list_ascii_trace_names(path):
    """List only full Smaart TF column groups; exclude RTA.

    Also used by GUI to force explicit choice when a .txt holds >1 traces.
    """
    lines=_text(path).splitlines()
    for i,line in enumerate(lines):
        value=line.lstrip("*; ").strip()
        if not value.lower().startswith("frequency (hz)\t"):continue
        fields=line.lstrip("*; ").strip().split("\t")
        labels=[x.strip().lower() for x in fields]
        names=lines[i-1].lstrip("*; ").split("\t") if i else []
        starts=[j for j,c in enumerate(labels) if c in ("magnitude (db)","level (db)")]
        found=[]
        for k,start in enumerate(starts):
            stop=starts[k+1] if k+1<len(starts) else len(fields)
            part=labels[start:stop]
            if (part[0]=="magnitude (db)" and "phase (degrees)" in part
                    and "coherence" in part):
                found.append(names[start].strip() if start<len(names)
                             and names[start].strip() else f"Trace {k+1}")
        return found
    return []
