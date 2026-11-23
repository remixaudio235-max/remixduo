"""V8.125: Auto FIR always creates a FIR; gates become warnings.

User 2026-11-12: "luôn tạo FIR, giảm bớt các điều kiện, gate an toàn,
cải thiện, mức Db, excess". strict=True (default) keeps the old HOLD
behaviour for other callers; the Duo panel uses strict=False.
"""
import numpy as np
import pytest

from remix_duo.core.filters import design_linear_phase_fir,design_phase_only_fir


def _tf(coh_value,n=400,delay_ms=1.0):
    f=np.geomspace(20,20000,n)
    rng=np.random.default_rng(1)
    phase=-2*np.pi*f*delay_ms/1000+.8*np.sin(np.log(f)*3)
    mag=10**((3*np.sin(np.log(f)*2)+rng.normal(0,.2,n))/20)
    h=mag*np.exp(1j*phase)
    return f,h,np.full(n,coh_value)


def test_strict_design_is_not_blocked_by_low_coherence():
    f,h,coh=_tf(.2)
    high=np.ones_like(coh)
    for design in (design_phase_only_fir,design_linear_phase_fir):
        low=design(f,h,coh,taps=1024,lf=100,hf=5000)
        trusted=design(f,h,high,taps=1024,lf=100,hf=5000)
        assert np.array_equal(low.taps,trusted.taps)


@pytest.mark.parametrize("taps",[512,1024,2048,4096])
def test_non_strict_low_coherence_still_creates_with_warning(taps):
    f,h,coh=_tf(.4)
    for result in (design_phase_only_fir(f,h,coh,taps=taps,lf=100,hf=5000,strict=False),
                   design_linear_phase_fir(f,h,coh,taps=taps,lf=100,hf=5000,strict=False)):
        assert len(result.taps)==taps and np.isfinite(result.taps).all()
        assert any("Coherence thấp" in w for w in result.warnings)


def test_nan_coherence_is_reference_only_when_tf_data_exists():
    f,h,coh=_tf(1.)
    coh[(f>=100)&(f<=5000)]=np.nan
    r=design_phase_only_fir(f,h,coh,taps=1024,lf=100,hf=5000,strict=False)
    trusted=design_phase_only_fir(f,h,np.ones_like(coh),taps=1024,
                                  lf=100,hf=5000,strict=False)
    assert np.array_equal(r.taps,trusted.taps)
    assert any("Coherence thấp" in w for w in r.warnings)


def test_short_taps_low_band_warns_instead_of_hold():
    f,h,coh=_tf(1.)
    r=design_phase_only_fir(f,h,coh,taps=512,lf=60,hf=1000,strict=False)
    assert len(r.taps)==512
    assert any("cần nhiều taps hơn" in w for w in r.warnings)


def test_phase_plus_gate_falls_back_to_regular_fir():
    f,h,coh=_tf(1.)
    regular=design_phase_only_fir(f,h,coh,taps=1024,lf=300,hf=5000,strict=False)
    plus=design_phase_only_fir(f,h,coh,taps=1024,lf=300,hf=5000,
                               phase_plus=True,strict=False)
    assert len(plus.taps)==1024 and np.isfinite(plus.taps).all()
    if any("Phase+ không đạt" in w for w in plus.warnings):
        assert np.array_equal(plus.taps,regular.taps)


def test_good_data_has_no_warnings_and_matches_strict():
    f,h,coh=_tf(1.)
    strict=design_phase_only_fir(f,h,coh,taps=2048,lf=300,hf=5000)
    relaxed=design_phase_only_fir(f,h,coh,taps=2048,lf=300,hf=5000,strict=False)
    assert np.array_equal(strict.taps,relaxed.taps)   # algorithm unchanged
    assert relaxed.warnings==()
