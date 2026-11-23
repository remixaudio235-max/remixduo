"""RemiX Dou V8.50: 1/4 octave, exact biquad and no overlap safety."""
import hashlib,math
from pathlib import Path
import numpy as np
import pytest
from trf_core import read_trf
from remix_autoeq_v05_adapter import design_remix_eq
from autoeq_spacing_v850 import close_pairs,MIN_SPACING_OCT
from engines.remix_autoeq_unified import AutoEQBand,cascade_biquads

P=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data/TUNNINNGGG-9.trf"


@pytest.fixture(scope="module")
def data():
    if not P.exists():pytest.skip("Actual read-only user TRF not present")
    src=read_trf(P)
    return src


@pytest.mark.parametrize("lo,hi,expected_count",[
    (60.,10730.,6),
    (83.,6870.,5),
    (75.,2440.,5),
])
def test_real_user_roi_no_overlap_exact_parity(data,lo,hi,expected_count):
    orig_sha=hashlib.sha256(P.read_bytes()).hexdigest()
    res=design_remix_eq(data.hz,data.h,data.coherence,
        fs=48000,target="Flat",filters=8,lf=lo,hf=hi,
        boost=2.,cut=-9.,source=P.stem)
    assert res.status=="PREVIEW_READY"
    assert len(res.peqs)==expected_count
    assert all(3.<=b.q<=8. for b in res.peqs)
    assert any("PEQ_SPACING_1_4_OCT" in t for t in res.warnings)
    bands=[AutoEQBand("P",b.freq_hz,b.gain_db,b.q) for b in res.peqs]
    assert not close_pairs(bands)
    assert all(lo<=b.f_hz<=hi and -9-1e-6<=b.gain_db<=2+1e-6
               for b in bands)
    assert all(math.log2(b.f_hz/a.f_hz)>=MIN_SPACING_OCT-1e-8
               for a,b in zip(sorted(bands,key=lambda b:b.f_hz),
                              sorted(bands,key=lambda b:b.f_hz)[1:]))
    mag_exact=res.before_db+20*np.log10(np.maximum(np.abs(
        cascade_biquads(res.hz,bands,48000)),1e-15))
    assert np.allclose(mag_exact,res.after_db,atol=1e-7)
    assert res.rms_after<res.rms_before
    assert hashlib.sha256(P.read_bytes()).hexdigest()==orig_sha


def test_flat_83hz_three_filters_become_one_not_zero(data):
    r=design_remix_eq(data.hz,data.h,data.coherence,
        fs=48000,target="Flat",filters=8,lf=83,hf=6870,
        boost=2.,cut=-9.)
    lf=[b for b in r.peqs if 90<=b.freq_hz<=125]
    assert len(lf)==1
    assert 101<lf[0].freq_hz<110
    assert -9<=lf[0].gain_db<0
    assert r.rms_after<=4.1


def test_190hz_rescue_kept_after_spacing(data):
    r=design_remix_eq(data.hz,data.h,data.coherence,
        fs=48000,target="Flat",filters=8,lf=75,hf=2440,
        boost=2.,cut=-9.)
    assert any("PEAK_CUT_RESCUE" in w or "PRACTICAL_Q_3_8_PEAK" in w
               for w in r.warnings)
    assert any("PEQ_SPACING_1_4_OCT" in w for w in r.warnings)
    assert any(185<=b.freq_hz<=195 and b.gain_db<-3 for b in r.peqs)
    assert abs(float(np.interp(190.,r.hz,r.after_db-r.target_db)))<1.
    assert r.rms_after<3.40


def test_house_profile_never_exports_clashing_peq(data):
    r=design_remix_eq(data.hz,data.h,data.coherence,
        fs=48000,target="House",filters=8,lf=83,hf=6870,
        boost=2.,cut=-9.)
    assert len(r.peqs)<=8
    assert not close_pairs(r.peqs)
    assert not any("PEAK_CUT_RESCUE" in w for w in r.warnings)


@pytest.mark.parametrize("filters",range(1,9))
def test_max_peq_is_upper_bound_every_config(data,filters):
    r=design_remix_eq(data.hz,data.h,data.coherence,
        fs=48000,target="Flat",filters=filters,lf=83,hf=6870,
        boost=2.,cut=-9.)
    assert len(r.peqs)<=filters
    assert not close_pairs(r.peqs)


def test_exact_minimum_ratio_is_allowed():
    f=100.0
    a=AutoEQBand("P",f,-3.,4.)
    b=AutoEQBand("P",f*2**MIN_SPACING_OCT,-4.,6.)
    assert not close_pairs((b,a))
    c=AutoEQBand("P",f*2**(MIN_SPACING_OCT-.005),-4.,6.)
    assert len(close_pairs((c,a)))==1
