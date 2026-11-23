"""V8.133: FIR MAG flattens around the trace's own level, not absolute 0 dB.

Live 2026-11-12 ("tạo FIR Mag gì kỳ cục"): TUNNINNGGG-13-1, 403-1420 Hz,
stored level ~+14 dB (Smaart showed +4 with a -10 dB trace offset). The old
0 dB target cut 8-12 dB and the band sank to -8..-10 dB on screen.
"""
import numpy as np
import pytest

from remix_duo.core.filters import design_linear_phase_fir


def _tf(level_db):
    f=np.geomspace(20,20000,900)
    ripple=3*np.sin(np.log2(f/400)*2.5)               # +-3 dB ripple
    h=10**((level_db+ripple)/20)*np.exp(-1j*2*np.pi*f*0.001)
    return f,h,np.ones_like(f),ripple


@pytest.mark.parametrize("level_db",[0.,14.,-20.])
def test_level_kept_ripple_flattened(level_db):
    f,h,coh,ripple=_tf(level_db)
    d=design_linear_phase_fir(f,h,coh,taps=2048,lf=400,hf=1400,strict=False)
    band=(f>=450)&(f<=1250)
    before=20*np.log10(np.abs(h[band]))
    after=before+np.interp(f[band],d.hz,d.actual_db)
    assert abs(np.median(after)-np.median(before))<1.0   # same level
    assert np.std(after)<0.5*np.std(before)                 # ripple flattened
    act=(d.hz>=400)&(d.hz<=1400)
    assert np.max(np.abs(d.actual_db[act]))<=4.5           # only the ripple


def test_offset_does_not_change_the_fir():
    a=design_linear_phase_fir(*_tf(0.)[:3],taps=1024,lf=400,hf=1400)
    b=design_linear_phase_fir(*_tf(14.)[:3],taps=1024,lf=400,hf=1400)
    assert np.allclose(a.taps,b.taps,atol=1e-9)
