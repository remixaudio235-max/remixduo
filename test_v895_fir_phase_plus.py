"""V8.95 Phase+ opt-in QA: measured TF + real Qt FIR worker, fail closed."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import numpy as np
import pytest
from trf_core import read_trf
from signal_tools_core_v813 import design_phase_only_fir
from remix_duo.core.fir_preview import phase_excess_rms
from test_v845_fir_one_trace import init,wait_fir
from test_v16_independent_one_tick import tick


def measured():
    p=(Path.home()/"Documents"/"Smaart Suite"/"Data"/
       "Transfer Function"/"Session Data"/"TUNNINNGGG-4.trf")
    if not p.exists():pytest.skip("Reference TRF unavailable")
    return p,read_trf(p)


def test_phase_plus_ab_measured_fir_is_real_causal_and_safely_better():
    p,tr=measured()
    baseline=design_phase_only_fir(tr.hz,tr.h,tr.coherence,4096,48000,
                                    lf=114,hf=379,source=p.stem)
    strong=design_phase_only_fir(tr.hz,tr.h,tr.coherence,4096,48000,
                                  lf=114,hf=379,source=p.stem,phase_plus=True)
    before,base_after,_,bins=phase_excess_rms(
        tr.hz,tr.h,tr.coherence,baseline.taps,48000,114,379)
    _,strong_after,improve,_=phase_excess_rms(
        tr.hz,tr.h,tr.coherence,strong.taps,48000,114,379)
    assert bins>=55
    assert before>30
    assert base_after>25
    assert strong_after<18
    assert strong_after<base_after*.85
    assert improve>50
    assert strong.mode=="phase" and len(strong.taps)==4096
    assert np.all(np.isfinite(strong.taps))
    assert np.max(np.abs(strong.actual_db[(strong.hz>=20)&
                                           (strong.hz<=20000)]))<=1.5
    mid=len(strong.taps)//2
    early=np.sum(strong.taps[:mid-int(.005*48000)]**2)/np.sum(strong.taps**2)
    assert early<.002
    assert strong.latency_ms==pytest.approx(42.65625)
    assert not np.allclose(strong.taps,baseline.taps,atol=1e-6)


def test_optin_short_fir_uses_safety_gate_and_rejects_low_coherence():
    _,tr=measured()
    # 1024-tap Phase+ is allowed to attempt, but this real low-frequency
    # trace fails physical safety limits; no automatic tap substitution.
    with pytest.raises(ValueError,match=r"FIR Phase\+ HOLD"):
        design_phase_only_fir(tr.hz,tr.h,tr.coherence,1024,48000,
                              lf=114,hf=379,phase_plus=True)
    with pytest.raises(ValueError):
        design_phase_only_fir(tr.hz,tr.h,np.zeros_like(tr.coherence),4096,
                              48000,lf=114,hf=379,phase_plus=True)


def test_phase_plus_qt_manual_optin_with_taps_freely_selectable():
    p,_=measured()
    app,obs,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        idx=next(i for i,x in enumerate(obs.order)
                 if x.name.lower()==p.name.lower())
        for _ in range(3):tick(obs,{idx})
        fir.refresh_sources()
        assert fir._fir_token and Path(fir._fir_token[0])==p
        assert fir.fir_mode.currentData()=="phase"
        assert fir.taps.currentData()==0 and fir.taps.currentText()=="AUTO taps"
        assert fir.taps.isEnabled()
        assert not fir.phase_plus.isChecked()
        assert not fir.phase_plus.isHidden()
        fir.fir_mode.setCurrentIndex(1)
        fir.fir_lf.setValue(114)
        fir.fir_hf.setValue(379)
        app.processEvents()
        assert not fir.phase_plus.isChecked()
        assert not fir.phase_plus.isHidden()  # parent may be hidden in offscreen QA
        for taps in (512,1024,2048,4096):
            fir.taps.setCurrentIndex(fir.taps.findData(taps))
            assert fir.taps.isEnabled()
            assert fir.taps.currentData()==taps
        fir.taps.setCurrentIndex(fir.taps.findData(4096))
        fir.phase_plus.setChecked(True)
        assert fir.taps.isEnabled()
        fir.compute()
        wait_fir(app,fir,timeout=20)
        assert fir.result is not None,fir.details.toPlainText()
        assert fir._approved_phase_plus is True
        assert fir._proof_current()
        assert fir.export_txt.isEnabled() and fir.export_wav.isEnabled()
        assert "Phase+" in fir.summary.text()
        assert "Excess RMS" in fir.summary.text()
        assert "42.66 ms" in fir.details.toPlainText()
        # When FIR PHASE leaves the screen, all prior FIR proof is discarded.
        fir.fir_mode.setCurrentIndex(0)
        assert fir._approved is None
        assert fir._approved_phase_plus is None
        assert not fir.export_wav.isEnabled()
        assert hub.native_fir.source is None
        assert fir.taps.isEnabled()
        fir.taps.setCurrentIndex(fir.taps.findData(1024))
        assert fir.taps.currentData()==1024
        fir.fir_mode.setCurrentIndex(1)
        assert fir.taps.currentData()==1024
        assert fir.taps.isEnabled()
        assert fir.phase_plus.isChecked()
        fir.phase_plus.setChecked(False)
        assert not fir.phase_plus.isChecked()
        assert fir.taps.currentData()==1024
        assert fir.taps.isEnabled()
    finally:
        hub.close()
        app.processEvents()
