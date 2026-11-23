"""Phase non-degradation regression: real TRFs + quality-cohort + adaptive strength."""
from pathlib import Path
import numpy as np,pytest
from trf_core import read_trf
from remix_duo.core.filters import design_phase_only_fir,design_linear_phase_fir
from remix_duo.core.fir_preview import make_source,phase_excess_rms
from remix_duo.core.fir_quality_gate import evaluate_fir_quality
from signal_tools_gui_v813 import _fir_design_and_preview
V8=Path.home()/"Documents/Smaart v8/Traces/Transfer Function/Session Data"
V9=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"

def get(name,edition=8):
 p=(V8 if edition==8 else V9)/name
 assert p.is_file()
 return read_trf(p)

def verdict(name,lf,hf,taps,strength=1.,edition=8):
 t=get(name,edition)
 r=design_phase_only_fir(t.hz,t.h,t.coherence,taps,48000,
                         lf=lf,hf=hf,strict=False,
                         correction_strength=strength)
 p=make_source(t.hz,t.h,t.coherence,r.taps,48000,name,"SHA",1,lf,hf,"phase")
 return evaluate_fir_quality(p,r,lf,hf),p,r

def test_true_trusted_phase_worsening_gets_hold():
 v,p,r=verdict("0 delay.trf",30,16000,4096)
 assert not v.accepted
 assert v.phase_after_deg>v.phase_before_deg+1.
 assert any("coherence" in reason for reason in v.reasons)
 # Both input arrays and FIR coefficients are physical, not GUI rasters.
 assert len(r.taps)==4096 and np.isfinite(r.taps).all()

def test_source_114_379_full_strength_worsens_lf_hold():
 v,p,r=verdict("0 delay.trf",114,379,4096,1.)
 assert not v.accepted
 assert v.phase_after_deg<v.phase_before_deg
 assert any("LF: Phase tệ hơn" in reason for reason in v.reasons)

def test_adaptive_quarter_strength_no_lf_hf_regression():
 v,p,r=verdict("0 delay.trf",114,379,4096,.25)
 assert v.accepted,v.reasons
 assert v.phase_after_deg<v.phase_before_deg*.95
 assert r.correction_strength==pytest.approx(.25)
 # Core preview stays all-bin for display; approval is trusted-only.
 assert p.phase_rms_after is not None and v.phase_after_deg is not None

def test_gui_auto_taps_phase_chooses_safe_4096_and_damped_strength():
 t=get("0 delay.trf")
 r,p=_fir_design_and_preview(t.hz,t.h,t.coherence,0,48000,
                              "0 delay","SHA",1,114,379,"phase",False,1/6)
 assert len(r.taps)==4096
 assert r.correction_strength==pytest.approx(.25)
 assert p.phase_rms_after < p.phase_rms_before
 assert "AUTO TAPS" in " ".join(map(str,r.warnings))

def test_gui_forced_unsafe_phase_512_returns_preview_only():
 t=get("0 delay.trf")
 result,preview=_fir_design_and_preview(t.hz,t.h,t.coherence,512,48000,
                         "0 delay","SHA",1,35,188,"phase",False,1/6)
 assert len(result.taps)==512 and preview.mode=="phase"
 assert any(str(w).startswith("PREVIEW_ONLY:") for w in result.warnings)

def test_low_coherence_hf_is_hold_even_if_old_rms_improves():
 v,p,r=verdict("SUB SKY 2.trf",114,379,4096)
 assert not v.accepted
 assert any("HF: chỉ" in reason for reason in v.reasons)

def test_suite_phase_lf_hf_third_guard_marks_preview_only():
 t=get("TUNNINNGGG-3-1.trf",9)
 v,p,r=verdict("TUNNINNGGG-3-1.trf",114,379,4096,1.,edition=9)
 assert not v.accepted
 assert any("HF_THIRD: Phase tệ hơn" in reason for reason in v.reasons)
 result,preview=_fir_design_and_preview(t.hz,t.h,t.coherence,0,48000,
                         "suite","SHA",1,114,379,"phase",False,1/6)
 assert result.taps.size and preview.mode=="phase"
 assert any(str(w).startswith("PREVIEW_ONLY:") for w in result.warnings)

def test_visual_phase_not_truncated_by_trusted_coherence_gate():
 t=get("SUB SKY 2.trf")
 r=design_phase_only_fir(t.hz,t.h,t.coherence,4096,48000,
                         lf=114,hf=379,strict=False)
 p=make_source(t.hz,t.h,t.coherence,r.taps,48000,
               "SOURCE","SHA",1,114,379,"phase")
 assert int(np.sum(p.phase_valid))>100
 # The displayed PHASE curve remains coherence-gate 0. Quality is
 # coherence-gated independently; a low-trust source remains HOLD.
 assert not evaluate_fir_quality(p,r,114,379).accepted

def test_mag_filter_is_linear_phase_after_removing_known_delay():
 t=get("0 delay.trf")
 r=design_linear_phase_fir(t.hz,t.h,t.coherence,1024,48000,
                           lf=35,hf=188,strict=False)
 from scipy.signal import freqz
 f=np.geomspace(35,188,128)
 _,resp=freqz(r.taps,worN=f,fs=48000)
 delay=(len(r.taps)-1)/(2*48000)
 err=np.angle(resp*np.exp(2j*np.pi*f*delay),deg=True)
 assert np.max(np.abs(err))<1.
