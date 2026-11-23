"""V8.131/V8.136: coherence never gates FIR preview or quality metrics.

User 2026-11-12 (live find 1,2ms-1): "gate coherence=0 để phase không bị
đứt nét". The preview phase and Excess RMS now use every valid TF bin;
coherence remains display/reference metadata only.
"""
import numpy as np

from remix_duo.core.fir_preview import PREVIEW_COHERENCE_GATE, make_source


def _src(coh_value):
    f=np.geomspace(20,20000,600)
    h=np.exp(-1j*2*np.pi*f*0.001)
    coh=np.full(f.shape,.95)
    coh[(f>500)&(f<700)]=coh_value          # a low-coherence stretch
    coh[(f>2000)&(f<2100)]=np.nan           # Smaart no-data bins
    k=np.zeros(1024);k[511]=k[512]=.5
    return f,make_source(f,h,coh,k,48000,"t","i",1,300,5000,"phase")


def test_gate_is_zero():
    assert PREVIEW_COHERENCE_GATE==0.


def test_low_or_nan_coherence_still_drawn_when_tf_is_valid():
    f,s=_src(.3)
    low=(f>500)&(f<700)
    assert s.phase_valid[low].all()            # no gap in the preview line
    assert s.phase_valid[(f>2000)&(f<2100)].all()


def test_quality_metric_uses_all_valid_tf_bins():
    f,s=_src(.3)
    valid=int(np.count_nonzero((f>=300)&(f<=5000)))
    assert s.phase_quality_bins==valid


def test_panel_and_strict_design_ignore_coherence():
    """V8.136: coherence is reference-only for every FIR caller."""
    import remix_duo.core.filters as F
    assert F.PANEL_COHERENCE_FLOOR==0.
    f=np.geomspace(20,20000,600)
    h=np.exp(1j*(np.deg2rad(30)*np.sin(np.log2(f))-2*np.pi*f*0.001))
    coh=np.full(f.shape,.4)                    # below every old gate
    r=F.design_phase_only_fir(f,h,coh,taps=1024,lf=600,hf=5000,strict=False)
    assert any("Coherence thấp" in w for w in r.warnings)   # informed, not blocked
    strict=F.design_phase_only_fir(f,h,coh,taps=1024,lf=600,hf=5000)
    assert np.array_equal(strict.taps,r.taps)
