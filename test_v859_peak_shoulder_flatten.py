"""V8.59: EQ5 must flatten coherent 96–110Hz shoulder, not only 109Hz apex."""
import hashlib
from pathlib import Path
import numpy as np
import pytest
from trf_core import read_trf
from remix_autoeq_v05_adapter import design_remix_eq
from autoeq_spacing_v850 import close_pairs
from autoeq_peak_shape_v859 import refine_cut_peak_shoulder
from engines.remix_autoeq_unified import (
    AutoEQBand,AutoEQProfile,AutoEQInput,prepare_analysis_curves,cascade_biquads
)

ROOT=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"


def test_real_nine_trace_eq5_shoulder_and_export_parity():
    path=ROOT/"TUNNINNGGG-9.trf"
    if not path.is_file():pytest.skip("Real read-only Smaart TF missing")
    sha=hashlib.sha256(path.read_bytes()).digest()
    tr=read_trf(path)
    r=design_remix_eq(tr.hz,tr.h,tr.coherence,fs=48000,target="Flat",
        filters=8,lf=60,hf=7900,boost=2,cut=-9,source=path.stem)
    assert r.status=="PREVIEW_READY" and len(r.peqs)==5
    eq5=r.peqs[-1]
    assert 102<=eq5.freq_hz<=108
    assert 3<=eq5.q<=7
    assert -9<=eq5.gain_db<0
    residual=r.after_db-r.target_db
    roi=(r.hz>=92)&(r.hz<=119)
    assert np.max(residual[roi])<=1.5
    assert np.min(residual[roi])>=-1.5
    assert r.rms_after<4.3
    assert any("PEAK_SHOULDER_REFINED" in x for x in r.warnings)
    bands=[AutoEQBand("P",b.freq_hz,b.gain_db,b.q) for b in r.peqs]
    assert not close_pairs(bands)
    assert all(3<=b.q<=8 and -9<=b.gain_db<=2 for b in bands)
    exact=r.before_db+20*np.log10(np.maximum(abs(
        cascade_biquads(r.hz,bands,48000)),1e-15))
    assert np.allclose(exact,r.after_db,atol=1e-7)
    assert hashlib.sha256(path.read_bytes()).digest()==sha


def test_shoulder_refinement_fails_closed_for_unreliable_measurements():
    path=ROOT/"TUNNINNGGG-9.trf"
    if not path.exists():pytest.skip("Real Smaart TF missing")
    t=read_trf(path)
    mask=(t.hz>=60)&(t.hz<=7900)&(t.coherence>=.60)&(abs(t.h)>1e-12)
    lev=float(np.median(20*np.log10(abs(t.h[mask]))))
    inp=AutoEQInput(t.hz,t.h*10**(-lev/20),np.zeros_like(t.coherence)+.31,
        "coherence",48000,"stored_tf",np.array([60.,7900.]),np.array([0.,0.]),6.)
    prof=AutoEQProfile(f_min_hz=60,f_max_hz=7900,max_filters=8,
        max_peq=8,max_boost_db=2,max_cut_db=-9,
        max_low_shelf=0,max_high_shelf=0,
        min_q=3,max_q=8,max_resonance_q=8)
    data=prepare_analysis_curves(inp,prof)
    original=np.zeros_like(data.grid_hz)
    band=AutoEQBand("P",109.,-5.5,8.)
    refined,pred,note=refine_cut_peak_shoulder(
        data,original,original,band,(),prof)
    assert refined==band
    assert note==""
    assert np.isfinite(pred).all()


@pytest.mark.parametrize("trace",["TUNNINNGGG-7.trf","TUNNINNGGG-8.trf"])
def test_related_traces_keep_peq_only_q_3_8_and_prediction(trace):
    path=ROOT/trace
    if not path.exists():pytest.skip("Real Smaart TF missing")
    t=read_trf(path)
    r=design_remix_eq(t.hz,t.h,t.coherence,fs=48000,target="Flat",
        filters=8,lf=60,hf=8000,boost=2,cut=-9,source=path.stem)
    assert r.status=="PREVIEW_READY" and len(r.peqs)<=8
    assert all(3<=b.q<=8 for b in r.peqs)
    assert not close_pairs(r.peqs)
    bands=[AutoEQBand("P",b.freq_hz,b.gain_db,b.q) for b in r.peqs]
    predicted=r.before_db+20*np.log10(np.maximum(abs(
        cascade_biquads(r.hz,bands,48000)),1e-15))
    assert np.allclose(predicted,r.after_db,atol=1e-7)
