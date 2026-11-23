"""Offline quality gate regression on real TRFs, no Smaart GUI/DSP changes."""
from pathlib import Path
import pytest
from trf_core import read_trf
from remix_duo.core.filters import design_phase_only_fir,design_linear_phase_fir
from remix_duo.core.fir_preview import make_source
from remix_duo.core.fir_quality_gate import evaluate_fir_quality
from signal_tools_gui_v813 import _fir_design_and_preview

V8=Path.home()/"Documents/Smaart v8/Traces/Transfer Function/Session Data"
V9=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"

def source(name,edition=8):
    p=(V8 if edition==8 else V9)/name
    assert p.is_file()
    tr=read_trf(p)
    return tr

def get_verdict(name,mode,taps,lf,hf,edition=8):
    tr=source(name,edition)
    kwargs=dict(taps=taps,fs=48000,lf=lf,hf=hf,strict=False)
    design=design_phase_only_fir if mode=="phase" else design_linear_phase_fir
    result=design(tr.hz,tr.h,tr.coherence,**kwargs)
    preview=make_source(tr.hz,tr.h,tr.coherence,result.taps,48000,
                        name,"qa",123,lf,hf,mode)
    return evaluate_fir_quality(preview,result,lf,hf)

def test_512tap_subwoofer_phase_zero_improvement_blocked():
    v=get_verdict("0 delay.trf","phase",512,35,188)
    assert not v.accepted
    assert v.phase_coverage_octaves==0
    assert any("độ phân giải" in r for r in v.reasons)

def test_4096tap_114_379_requires_adaptive_phase_strength():
    from remix_duo.core.fir_preview import make_source
    from remix_duo.core.fir_quality_gate import evaluate_fir_quality
    tr=source("0 delay.trf")
    raw=get_verdict("0 delay.trf","phase",4096,114,379)
    assert not raw.accepted  # whole-band improves but LF section gets worse
    r=design_phase_only_fir(tr.hz,tr.h,tr.coherence,taps=4096,fs=48000,
                            lf=114,hf=379,strict=False,correction_strength=.25)
    p=make_source(tr.hz,tr.h,tr.coherence,r.taps,48000,
                  "QA","QA",1,114,379,"phase")
    safe=evaluate_fir_quality(p,r,114,379)
    assert safe.phase_before_deg>safe.phase_after_deg
    assert safe.phase_coverage_octaves>=1
    assert safe.accepted,safe.reasons

def test_unhelpful_mag_512_not_exportable():
    v=get_verdict("TUNNINNGGG-3-1.trf","mag",512,35,188,edition=9)
    assert not v.accepted
    assert v.mag_rms_before_db-v.mag_rms_after_db<.2
    assert any("RMS MAG" in reason for reason in v.reasons)

def test_synthetic_actual_boost_overshoot_blocked():
    # Deliberately corrupt an otherwise valid FIR to prove the gate follows
    # physical taps instead of trusting the +/-6dB design target.
    from dataclasses import replace
    from remix_duo.core.fir_quality_gate import evaluate_fir_quality
    from remix_duo.core.fir_preview import make_source
    tr=source("TUNNINNGGG-3-1.trf",edition=9)
    result=design_linear_phase_fir(tr.hz,tr.h,tr.coherence,taps=4096,fs=48000,
                                   lf=35,hf=188,strict=False)
    corrupted=replace(result,taps=result.taps*2.)
    preview=make_source(tr.hz,tr.h,tr.coherence,corrupted.taps,48000,
                        "TUNNINNGGG-3-1","synthetic_fault",4,35,188,"mag")
    v=evaluate_fir_quality(preview,corrupted,35,188)
    assert not v.accepted
    assert v.max_filter_boost_db>6.5
    assert any("Boost FIR thực" in reason for reason in v.reasons)

def test_gui_worker_previews_phase_without_usable_lf_hf():
    tr=source("0 delay.trf")
    result,preview=_fir_design_and_preview(
        tr.hz,tr.h,tr.coherence,512,48000,
        "0 delay","qa",88,35,188,"phase",False,1/6)
    assert len(result.taps)==512 and preview.mode=="phase"
    assert any(str(w).startswith("PREVIEW_ONLY:") for w in result.warnings)
