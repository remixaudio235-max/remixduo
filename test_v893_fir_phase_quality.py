"""V8.93 Phase FIR QA: original complex H, real taps, honest residual metrics."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import numpy as np
import pytest

from trf_core import read_trf
from pathlib import Path
from scipy.signal import freqz

from signal_tools_core_v813 import design_phase_only_fir
from remix_duo.core.fir_preview import make_source,phase_excess_rms
from test_v845_fir_one_trace import init,wait_fir


def test_measured_phase_quality_proves_short_low_band_fir_is_not_flat():
    p=(Path.home()/"Documents"/"Smaart Suite"/"Data"/
       "Transfer Function"/"Session Data"/"TUNNINNGGG-4.trf")
    if not p.is_file():pytest.skip("Reference TRF not on this machine")
    tr=read_trf(p)
    results=[]
    for taps in (1024,2048,4096):
        fir=design_phase_only_fir(tr.hz,tr.h,tr.coherence,taps=taps,
                                  fs=48000,lf=111,hf=310,source=p.stem)
        copy=fir.taps.copy()
        src=make_source(tr.hz,tr.h,tr.coherence,fir.taps,48000,
                        p.stem,"sha",7,111,310,"phase")
        assert src.phase_quality_bins>=35
        assert src.phase_rms_before>25
        assert src.phase_rms_after>0
        assert src.phase_improvement_pct is not None
        assert np.array_equal(fir.taps,copy)  # diagnostic never edits taps
        results.append((src.phase_rms_after,src.phase_improvement_pct))
    # 1024 has little phase authority around ~100 Hz on this exact measured TF.
    assert results[0][1] < 10,results
    assert results[2][0] < results[0][0],results


def test_real_fir_phase_summary_reports_rms_and_not_an_absolute_flat_phase():
    app,obs,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        fir.fir_mode.setCurrentIndex(1)
        fir.fir_lf.setValue(368)
        fir.fir_hf.setValue(3350)
        fir.compute()
        wait_fir(app,fir)
        assert fir.result is None
        assert "QUALITY HOLD" in fir.details.toPlainText()
        assert "coherence≥0.65" in fir.details.toPlainText()
        assert not fir.export_wav.isEnabled()
    finally:
        hub.close()
        app.processEvents()


def test_mag_mode_diagnostics_disabled_and_physical_phase_keeps_delay():
    f=np.geomspace(30,14000,160)
    h=np.ones_like(f,dtype=complex)
    coh=np.ones_like(f)
    taps=np.zeros(1024)
    taps[511]=.5
    taps[512]=.5
    src=make_source(f,h,coh,taps,48000,"synthetic","sha",2,111,310,"mag")
    assert src.phase_rms_before is None and src.phase_quality_bins==0
    assert src.phase_improvement_pct is None
    # A causal tap remains causal in the exported/physical phase.
    _,resp=freqz(taps,worN=f,fs=48000)
    expected=np.rad2deg(np.angle(h*resp))
    circular=lambda a,b:(a-b+180)%360-180
    assert np.max(np.abs(circular(src.after_phase,expected)))<1.5
