import numpy as np
import pytest
from scipy.signal import freqz
from signal_tools_core_v813 import design_phase_only_fir,design_linear_phase_fir

def trace():
    f=np.geomspace(20,20000,1500)
    # Smooth frequency-dependent phase + bulk propagation delay.
    excess=np.deg2rad(35)*np.exp(-.5*(np.log2(f/1000)/.8)**2)
    h=np.exp(1j*(excess-2*np.pi*f*.003)) * 10**(3*np.exp(-.5*(np.log2(f/300)/.4)**2)/20)
    return f,h,np.ones_like(f),excess

def test_phase_solver_preserves_mag_and_corrects_excess():
    f,h,coh,excess=trace()
    out=design_phase_only_fir(f,h,coh,taps=1024,fs=48000,lf=200,hf=6000)
    assert out.mode=="phase"
    assert len(out.taps)==1024
    assert np.all(np.isfinite(out.taps))
    assert not np.allclose(out.taps,out.taps[::-1],atol=1e-7)
    _,resp=freqz(out.taps,worN=f,fs=48000)
    band=(f>450)&(f<3000)
    comp=resp*np.exp(2j*np.pi*f*out.latency_ms/1000)
    residual=np.unwrap(np.angle(comp))
    assert np.median(np.abs(20*np.log10(np.abs(resp[band]))))<1.2
    assert np.abs(np.angle(comp[np.argmin(abs(f-1000))]))>np.deg2rad(3)

def test_mag_mode_stays_symmetric():
    f,h,c,_=trace()
    out=design_linear_phase_fir(f,h,c,1024,48000,lf=200,hf=6000)
    assert out.mode=="mag"
    assert np.allclose(out.taps,out.taps[::-1],atol=1e-10)

def test_phase_uses_low_coherence_as_reference_only():
    f,h,c,_=trace()
    out=design_phase_only_fir(f,h,c*0,1024,48000,lf=200,hf=6000)
    assert len(out.taps)==1024
    assert any("Coherence thấp" in warning for warning in out.warnings)
