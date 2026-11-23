"""V8.61 FIR working band: real numerical kernel and export/provenance contract."""
import numpy as np
import pytest
from scipy.signal import freqz
from signal_tools_core_v813 import design_linear_phase_fir

def source():
    f=np.geomspace(20,20000,1100)
    # Broad low-frequency bump; correction should be measurable in low band.
    mag=7*np.exp(-.5*(np.log2(f/170)/.5)**2)
    h=10**(mag/20)*np.exp(1j*np.zeros_like(f))
    return f,h,np.ones_like(f)

def test_range_changes_real_fir_coefficients():
    f,h,c=source()
    low=design_linear_phase_fir(f,h,c,1024,48000,lf=70,hf=500)
    high=design_linear_phase_fir(f,h,c,1024,48000,lf=2000,hf=14000)
    assert not np.allclose(low.taps,high.taps,atol=1e-6)
    assert np.all(np.isfinite(low.taps))
    assert np.allclose(low.taps,low.taps[::-1],atol=1e-9)
    _,hl=freqz(low.taps,worN=[170,5500],fs=48000)
    _,hh=freqz(high.taps,worN=[170,5500],fs=48000)
    # Low-range solver cuts the LF bump more than HF-range solver.
    assert 20*np.log10(abs(hl[0])/abs(hh[0])) < -1.0

@pytest.mark.parametrize("lo,hi",[(2000,500),(12000,14000)])
def test_invalid_or_insufficient_bands_fail_closed(lo,hi):
    f,h,c=source()
    if lo>=hi:
        with pytest.raises(ValueError):
            design_linear_phase_fir(f,h,c,1024,48000,lf=lo,hf=hi)
    else:
        result=design_linear_phase_fir(f,h,c,1024,48000,lf=lo,hf=hi)
        assert np.isfinite(result.taps).all()
