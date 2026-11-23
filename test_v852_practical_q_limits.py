"""V8.52: speaker AutoEQ defaults to a REAL Q range 3..8, not export-only clamps."""
from pathlib import Path
import hashlib
import numpy as np
import pytest
from trf_core import read_trf
from remix_autoeq_v05_adapter import design_remix_eq
from autoeq_q_policy_v852 import Q_MIN,Q_MAX,q_in_bounds
from autoeq_spacing_v850 import close_pairs
from autoeq_export_dialog_v08 import EQExportSnapshot
from engines.remix_autoeq_unified import AutoEQBand,cascade_biquads,AutoEQProfile

SOURCE=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data/TUNNINNGGG-9.trf"


@pytest.fixture(scope="module")
def source():
    if not SOURCE.is_file():pytest.skip("Smaart TRF missing")
    return read_trf(SOURCE)


@pytest.mark.parametrize("lo,hi",[(60.,10730.),(83.,6870.),(75.,2440.)])
def test_real_smaart_auto_eq_q_3_to_8_and_exact_mageq(source,lo,hi):
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    r=design_remix_eq(source.hz,source.h,source.coherence,
        fs=48000,target="Flat",filters=8,lf=lo,hf=hi,boost=2.,cut=-9.,
        source=SOURCE.stem)
    assert r.status=="PREVIEW_READY" and 1<=len(r.peqs)<=8
    assert q_in_bounds(r.peqs)
    assert not close_pairs(r.peqs)
    assert all(lo<=b.freq_hz<=hi and -9<=b.gain_db<=2 for b in r.peqs)
    raw=[AutoEQBand("P",b.freq_hz,b.gain_db,b.q) for b in r.peqs]
    corrected=r.before_db+20*np.log10(np.maximum(abs(
        cascade_biquads(r.hz,raw,48000)),1e-15))
    assert np.allclose(corrected,r.after_db,atol=1e-7)
    assert r.rms_after<r.rms_before
    snap=EQExportSnapshot.from_result(r,"Flat")
    assert len(snap.rows)==len(r.peqs)
    assert all(Q_MIN<=line.q<=Q_MAX for line in snap.rows)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sha


def test_sparse_190hz_notch_rescued_without_q12(source):
    r=design_remix_eq(source.hz,source.h,source.coherence,
        fs=48000,target="Flat",filters=8,lf=75.,hf=2440.,
        boost=2.,cut=-9.)
    assert any(185<=b.freq_hz<=195 and b.gain_db<-3.
               and 3<=b.q<=8 for b in r.peqs)
    assert abs(float(np.interp(190,r.hz,r.after_db-r.target_db)))<1.
    assert r.rms_after<3.4


def test_60hz_roi_corrects_two_user_circled_peaks_with_q_3_to_8(source):
    r=design_remix_eq(source.hz,source.h,source.coherence,
        fs=48000,target="Flat",filters=8,lf=60.,hf=10730.,
        boost=2.,cut=-9.)
    for center in (110.,190.):
        assert abs(float(np.interp(center,r.hz,r.after_db-r.target_db)))<1.3
    assert any("PRACTICAL_Q_3_8_PEAK" in w for w in r.warnings)
    assert q_in_bounds(r.peqs)


@pytest.mark.parametrize("target",["House","Tilt"])
def test_house_and_tilt_follow_q_policy_not_flat_only(source,target):
    r=design_remix_eq(source.hz,source.h,source.coherence,
        fs=48000,target=target,filters=8,lf=60.,hf=8000.,
        boost=2.,cut=-9.)
    assert len(r.peqs)<=8
    assert q_in_bounds(r.peqs)
    assert not close_pairs(r.peqs)
    assert all(-9<=b.gain_db<=2 for b in r.peqs)


@pytest.mark.parametrize("budget",range(1,9))
def test_q_policy_all_peq_budgets_no_hidden_q16(source,budget):
    r=design_remix_eq(source.hz,source.h,source.coherence,
        fs=48000,target="Flat",filters=budget,lf=83.,hf=6870.,
        boost=2.,cut=-9.)
    assert len(r.peqs)<=budget
    assert q_in_bounds(r.peqs)
    assert not close_pairs(r.peqs)


def test_default_engine_not_globally_mutated():
    assert AutoEQProfile().min_q==.30
    assert AutoEQProfile().max_resonance_q==16.
    assert Q_MIN==3. and Q_MAX==8.
