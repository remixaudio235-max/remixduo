"""V8.49 regression: authentic Smaart residual peaks, 8-PEQ safety & parity."""
from pathlib import Path
import hashlib
import numpy as np
import pytest
from trf_core import read_trf
from remix_autoeq_v05_adapter import design_remix_eq
from autoeq_peak_rescue_v849 import rescue_full_band_peak
from engines.remix_autoeq_unified import (
    AutoEQBand,AutoEQInput,AutoEQProfile,design_unified_autoeq,
    prepare_analysis_curves,cascade_biquads,compute_metrics
)

SOURCE=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data/TUNNINNGGG-9.trf"


@pytest.fixture(scope="module")
def trace():
    if not SOURCE.is_file(): pytest.skip("Real Smaart TRF not present")
    return read_trf(SOURCE)


@pytest.fixture(scope="module")
def models(trace):
    f,h,c=trace.hz,trace.h,trace.coherence
    opts=dict(fs=48000,target="Flat",filters=8,lf=75,hf=2440,
              boost=2,cut=-9,source=SOURCE.stem)
    after=design_remix_eq(f,h,c,**opts)
    mask=(f>=75)&(f<=2440)&(c>=.6)&(abs(h)>1e-12)
    level=float(np.median(20*np.log10(np.maximum(abs(h[mask]),1e-15))))
    inp=AutoEQInput(f,h*10**(-level/20),c,"coherence",48000,
        "stored_tf",np.array([75.,2440.]),np.array([0.,0.]),6.)
    profile=AutoEQProfile(f_min_hz=75.,f_max_hz=2440.,max_filters=8,
        max_peq=8,max_boost_db=2,max_cut_db=-9,
        min_q=3.,max_q=8.,max_resonance_q=8.)
    before=design_unified_autoeq(inp,profile)
    return inp,profile,before,after


def test_correct_190hz_peak_with_practical_q_and_bounded_peq_budget(models):
    inp,prof,old,r=models
    assert old.status=="PREVIEW_READY" and 1<=len(old.bands)<=8
    assert r.status=="PREVIEW_READY" and 1<=len(r.peqs)<=8
    assert any("PEAK_CUT_RESCUE" in w or "PRACTICAL_Q_3_8_PEAK" in w
               for w in r.warnings)
    peak_before=float(np.interp(190,old.freqs_hz,
        old.mag_pred_db-old.target_db))
    peak_after=float(np.interp(190,r.hz,r.after_db-r.target_db))
    assert peak_before>5.0
    assert abs(peak_after)<1.0
    assert np.max((r.after_db-r.target_db)[
        (r.hz>=175)&(r.hz<=205)])<2.1
    assert r.rms_after<old.after.weighted_rms_db-.05
    # Under Q<=8, separate broad/null-adjacent 110 Hz cannot be forced
    # with a prohibited ultra-narrow Q16 filter.
    assert abs(float(np.interp(110,r.hz,r.after_db-r.target_db)))<3.0
    rescued=[b for b in r.peqs if 185<b.freq_hz<195 and b.gain_db<0]
    assert len(rescued)==1
    assert 3<=rescued[0].q<=8 and rescued[0].gain_db>=-9


def test_source_sha_and_exact_peq_cascade_trace_parity(trace,models):
    before_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    inp,prof,old,r=models
    band=[AutoEQBand("P",b.freq_hz,b.gain_db,b.q) for b in r.peqs]
    eq=cascade_biquads(r.hz,band,48000)
    exact=r.before_db+20*np.log10(np.maximum(abs(eq),1e-15))
    assert np.allclose(r.after_db,exact,atol=1e-7)
    assert np.array_equal(trace.h,read_trf(SOURCE).h)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==before_sha
    assert len(band)<=8 and all(-9<=b.gain_db<=2 and
                                3<=b.q<=8 for b in band)


def test_peak_rescue_never_mutates_unified_solver_or_nonflat_target(models):
    inp,prof,base,r=models
    b=tuple(base.bands)
    safe,mag,warnings=rescue_full_band_peak(inp,prof,base,b,target_kind="House")
    assert safe==b and not warnings and np.array_equal(mag,base.mag_pred_db)
    safe,mag,warnings=rescue_full_band_peak(inp,prof,base,b[:-1],target_kind="Flat")
    assert safe==b[:-1] and not warnings and np.array_equal(mag,base.mag_pred_db)
    assert b==tuple(base.bands)
    assert r.status==base.status


def test_guard_metrics_and_neighbor_nulls(models):
    inp,prof,base,r=models
    data=prepare_analysis_curves(inp,prof)
    old=base.after
    rescue=[AutoEQBand("P",b.freq_hz,b.gain_db,b.q) for b in r.peqs]
    met=compute_metrics(data,r.target_db,r.after_db,rescue)
    assert abs(met.weighted_rms_db-r.rms_after)<1e-7
    assert met.p90_abs_error_db<=old.p90_abs_error_db+.35
    assert met.worst_abs_error_db<=old.worst_abs_error_db+.30
    original_res=np.asarray(base.mag_pred_db)-base.target_db
    protected=((data.quality>=.8)&(data.reliability>=.7)&
               (~data.deep_null_mask)&(data.weights>1e-5)&
               (original_res<=-1.5))
    assert np.min((r.after_db-base.mag_pred_db)[protected])>=-1.251


def test_low_coherence_peak_not_eligible(models):
    inp,prof,old,_=models
    import dataclasses
    weak=dataclasses.replace(inp,quality=np.zeros_like(inp.quality)+.31)
    bands=tuple(old.bands)
    new,mag,warn=rescue_full_band_peak(weak,prof,old,bands,target_kind="Flat")
    assert new==bands and not warn and np.array_equal(mag,old.mag_pred_db)
