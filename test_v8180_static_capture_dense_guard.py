"""Regress static Capture->FIR design->dense physical guard; no live audio."""
from pathlib import Path
from dataclasses import replace
import numpy as np
from scipy.signal import freqz
from trf_core import read_trf
from remix_duo.core.filters import design_phase_only_fir
from remix_duo.core.fir_preview import (
    phase_guard_reference,phase_guard_score,phase_dense_delay_guard,
    fir_response_on_grid,make_source)
from remix_duo.core.fir_quality_gate import evaluate_fir_quality

FS=48000
V8=Path.home()/"Documents/Smaart v8/Traces/Transfer Function/Session Data"
SUITE=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"

def test_100hz_sparse_sample_hides_10ms_but_dense_grid_rejects():
    n=2049
    sf=np.arange(100.,10001,100.)
    phase=np.deg2rad(32)*np.sin(np.log2(sf/1000.)*1.3)
    measured=np.exp(1j*(phase-2*np.pi*sf*.0073))
    reference=phase_guard_reference(sf,measured,np.ones_like(sf),100,10000,gate=.65)
    a=np.zeros(n);a[1024]=1.
    b=np.zeros(n);b[1504]=1.
    before_a,after_a,_,_=phase_guard_score(reference,a,FS,100,10000)
    before_b,after_b,_,_=phase_guard_score(reference,b,FS,100,10000)
    assert abs(before_a-before_b)<1e-8 and abs(after_a-after_b)<1e-8
    fft_f=np.fft.rfftfreq(32768,1/FS)
    ok1,_,delay1=phase_dense_delay_guard(a,FS,fft_f,np.zeros_like(fft_f))
    ok2,reason,delay2=phase_dense_delay_guard(b,FS,fft_f,np.zeros_like(fft_f))
    assert ok1 and abs(delay1)<.01
    assert not ok2 and "unintended dense FIR delay" in reason and abs(delay2-10)<.01

def test_v8180_actual_captured_filter_kernel_shift_denied():
    tr=read_trf(V8/"0 delay.trf")
    r=design_phase_only_fir(tr.hz,tr.h,tr.coherence,taps=4096,fs=FS,
                            lf=114,hf=379,strict=False,correction_strength=.25)
    good=make_source(tr.hz,tr.h,tr.coherence,r.taps,FS,"0 delay","qa",1,114,379,"phase")
    assert evaluate_fir_quality(good,r,114,379).accepted
    shifted=replace(r,taps=np.roll(r.taps,480))
    damaged=make_source(tr.hz,tr.h,tr.coherence,shifted.taps,FS,"0 delay","qa",1,114,379,"phase")
    gate=evaluate_fir_quality(damaged,shifted,114,379)
    assert not gate.accepted
    assert any("unintended dense FIR delay" in x for x in gate.reasons),gate.reasons

def test_missing_target_and_untrusted_captured_data_fail_closed():
    tr=read_trf(V8/"0 delay.trf")
    r=design_phase_only_fir(tr.hz,tr.h,tr.coherence,taps=4096,fs=FS,
                            lf=114,hf=379,strict=False,correction_strength=.25)
    preview=make_source(tr.hz,tr.h,tr.coherence,r.taps,FS,"0 delay","qa",1,114,379,"phase")
    assert not evaluate_fir_quality(preview,replace(r,phase_target_rad=None),114,379).accepted
    missing=make_source(tr.hz,tr.h,np.zeros_like(tr.coherence),r.taps,FS,"0 delay","qa",1,114,379,"phase")
    assert not evaluate_fir_quality(missing,r,114,379).accepted

def test_recorded_fir_fft_fastpath_real_kernel_2048():
    tr=read_trf(SUITE/"TUNNINNGGG-3-1.trf")
    r=design_phase_only_fir(tr.hz,tr.h,tr.coherence,taps=2048,fs=FS,
                            lf=159,hf=11700,strict=False)
    f=r.hz
    fast=fir_response_on_grid(r.taps,FS,f)
    _,reference=freqz(r.taps,worN=f[::37],fs=FS)
    assert np.max(np.abs(fast[::37]-reference))<1e-7
    assert np.isfinite(r.phase_target_rad).all()
