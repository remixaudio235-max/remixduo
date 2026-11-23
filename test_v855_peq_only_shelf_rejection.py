"""V8.55 regression for original solver LS under Cut=-9 in TUNNINNGGG-7.

The unified core retains its shelf-capable defaults, but explicitly
honors zero shelf budget requested by RemiX Dou AutoEQ.
"""
import hashlib
from pathlib import Path
import numpy as np
import pytest
from engines.remix_autoeq_unified import (
    AutoEQProfile,AutoEQInput,detect_broad_shelf_candidate,
    design_unified_autoeq,prepare_analysis_curves,AutoEQBand,cascade_biquads)
from remix_autoeq_v05_adapter import design_remix_eq,target_anchors
from autoeq_spacing_v850 import close_pairs

ROOT=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"


@pytest.mark.parametrize("file,lf,hf",[
    ("TUNNINNGGG-7.trf",60.,8000.),
    ("TUNNINNGGG-8.trf",60.,8000.),
    ("TUNNINNGGG-9.trf",60.,10730.),
])
def test_auto_eq_original_trf_never_outputs_shelf(file,lf,hf):
    from trf_core import read_trf
    path=ROOT/file
    if not path.exists():pytest.skip("Test requires real user TRF")
    original_hash=hashlib.sha256(path.read_bytes()).digest()
    trace=read_trf(path)
    result=design_remix_eq(trace.hz,trace.h,trace.coherence,
        fs=48000,target="Flat",filters=8,lf=lf,hf=hf,
        boost=2.,cut=-9.,source=path.stem)
    assert result.status=="PREVIEW_READY"
    assert 1<=len(result.peqs)<=8
    assert not close_pairs(result.peqs)
    assert all(3<=b.q<=8 and -9<=b.gain_db<=2 and
               lf<=b.freq_hz<=hf for b in result.peqs)
    bands=[AutoEQBand("P",b.freq_hz,b.gain_db,b.q) for b in result.peqs]
    exact=result.before_db+20*np.log10(np.maximum(np.abs(
        cascade_biquads(result.hz,bands,48000)),1e-15))
    assert np.allclose(exact,result.after_db,atol=1e-7)
    assert result.rms_after<result.rms_before
    assert hashlib.sha256(path.read_bytes()).digest()==original_hash


def test_zero_shelf_budget_is_honored_by_unified_candidate_generator():
    from trf_core import read_trf
    path=ROOT/"TUNNINNGGG-7.trf"
    if not path.exists():pytest.skip("Test requires real TRF")
    tr=read_trf(path)
    mask=(tr.hz>=60)&(tr.hz<=8000)&(tr.coherence>=.6)&(abs(tr.h)>1e-12)
    level=float(np.median(20*np.log10(abs(tr.h[mask]))))
    anchors,db=target_anchors("Flat",60.,8000.)
    inp=AutoEQInput(tr.hz,tr.h*10**(-level/20),tr.coherence,
        "coherence",48000,"stored_tf",anchors,db,6.)
    profile=AutoEQProfile(f_min_hz=60,f_max_hz=8000,max_filters=8,
        max_peq=8,max_boost_db=2,max_cut_db=-9,min_q=3,
        max_q=8,max_resonance_q=8,max_low_shelf=0,max_high_shelf=0)
    data=prepare_analysis_curves(inp,profile)
    assert detect_broad_shelf_candidate(data,np.zeros_like(data.grid_hz),
                                        profile)==[]
    plan=design_unified_autoeq(inp,profile)
    assert all(b.type=="P" for b in plan.bands)
    assert AutoEQProfile().max_low_shelf==1
    assert AutoEQProfile().max_high_shelf==1


def test_shelves_can_be_requested_by_unified_engine_without_dou_policy():
    assert AutoEQProfile(max_low_shelf=1,max_high_shelf=1).max_low_shelf==1
    assert AutoEQProfile(max_low_shelf=1,max_high_shelf=1).max_high_shelf==1
