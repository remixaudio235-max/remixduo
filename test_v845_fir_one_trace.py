"""FIR V8.45 — one-tick Smaart identity / saved Fs / async + export safety.

Read-only originals, QA file outputs only in pytest temp dir.
"""
import hashlib
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication,QFileDialog

from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from signal_tools_core_v813 import FIRResult,save_fir_txt,save_fir_wav_float
from test_v16_independent_one_tick import setup,tick


def wait_fs(app,hub,timeout=2.0):
    until=time.monotonic()+timeout
    while hub.eq.fs.currentData() is None and time.monotonic()<until:
        hub.eq._refresh_fs(force=True)
        hub.fir.refresh_sources()
        app.processEvents()
        time.sleep(.01)
    hub.fir.refresh_sources()


def init(one=True):
    app=QApplication.instance() or QApplication([])
    obs=setup()
    if one:
        for _ in range(3):
            tick(obs,{0})
    engine=App(False)
    engine.timer.stop()
    engine.observer=obs
    engine.current_pair=None
    engine.current_traces=None
    engine._selection_verified=False
    hub=ToolHub(engine)
    hub.timer.stop()
    hub.native_eq.timer.stop()
    hub.select("fir")
    app.processEvents()
    wait_fs(app,hub)
    return app,obs,engine,hub,hub.fir


def wait_fir(app,fir,timeout=14):
    until=time.monotonic()+timeout
    while fir.result is None and fir.calculate.isEnabled() is False and time.monotonic()<until:
        # Simulate the fixture's unchanged full-page observations while the
        # solver runs. Real production polls independently; freezing a test
        # observer for >1.5s intentionally expires its authorization.
        obs=getattr(fir.engine,'observer',None)
        if obs is not None and callable(getattr(obs,'observe_single',None)):
            obs.observe_single(time.perf_counter())
        app.processEvents()
        time.sleep(.015)
    app.processEvents()


def test_fir_rejects_zero_two_six_and_allows_one_tick_without_auto_phase():
    app,obs,engine,hub,fir=init(one=False)
    try:
        assert not fir.source.isEnabled()
        assert fir.source.currentData() is None
        assert not fir.export_txt.isEnabled() and not fir.export_wav.isEnabled()
        for ids in ({0,1},{0,1,2,3,4,5},set()):
            tick(obs,ids)
            fir.refresh_sources()
            assert fir.source.currentData() is None
            with pytest.raises(ValueError,match="1 Trace"):
                fir.get_data()
        for _ in range(3):
            tick(obs,{0})
        fir.refresh_sources()
        assert fir.source.currentData()==0
        assert obs.order[0].stem in fir.source.itemText(0)
        assert fir._fir_fs and fir._fir_fs.hz==48000
        assert not fir.source.isEnabled()
        assert engine.current_pair is None
        data=fir.get_data()
        assert data[0].size>50 and data[3]==obs.order[0].stem
    finally:
        hub.close();app.processEvents()


def test_fir_worker_and_export_exact_source_snapshot(tmp_path,monkeypatch):
    app,obs,engine,hub,fir=init()
    try:
        # This scenario validates symmetric MAG FIR coefficients.
        fir.fir_mag_button.click()
        initial=obs.order[0]
        before=hashlib.sha256(initial.read_bytes()).hexdigest()
        fir.taps.setCurrentIndex(fir.taps.findData(1024))
        assert fir.taps.currentData()==1024
        assert not fir.export_txt.isEnabled()
        fir.compute()
        assert not fir.calculate.isEnabled()
        wait_fir(app,fir)
        assert fir.result is not None,fir.details.toPlainText()
        assert fir.result.fs==48000
        assert len(fir.result.taps)==1024
        assert fir._proof_current()
        assert fir.export_txt.isEnabled() and fir.export_wav.isEnabled()
        assert np.allclose(fir.result.taps,fir.result.taps[::-1],atol=1e-9)
        assert abs(fir.result.latency_ms-1023/96000*1000)<1e-7
        assert hashlib.sha256(initial.read_bytes()).hexdigest()==before
        # Different source bytes despite same name/stat must gate both exports.
        old_hash=fir._source_hash
        monkeypatch.setattr(fir,"_source_hash",lambda path:"other-sha")
        fir._refresh_export()
        assert not fir.export_txt.isEnabled() and not fir.export_wav.isEnabled()
        monkeypatch.setattr(fir,"_source_hash",old_hash)
        fir._refresh_export()
        assert fir.export_txt.isEnabled() and fir.export_wav.isEnabled()
        txt=tmp_path/"fir.txt"
        wav=tmp_path/"fir.wav"
        monkeypatch.setattr(QFileDialog,"getSaveFileName",
                            lambda *a,**k:(str(wav if "WAV" in str(a[1]) else txt),""))
        fir.save_txt()
        fir.save_wav()
        assert txt.exists() and wav.exists()
        assert len(txt.read_text(encoding="utf8").splitlines())==1026
        import struct
        data=wav.read_bytes()
        assert data[:4]==b"RIFF" and data[8:12]==b"WAVE"
        assert struct.unpack_from("<H",data,20)[0]==3
        assert struct.unpack_from("<I",data,24)[0]==48000
        assert len(data)==44+4*1024
        # New Smaart tick invalidates the old accepted kernel + export.
        tick(obs,{0,1})
        fir.refresh_sources()
        assert fir.result is None
        assert not fir.export_txt.isEnabled() and not fir.export_wav.isEnabled()
    finally:
        hub.close();app.processEvents()


def test_fir_saved_fs_change_and_source_bytes_change_fail_closed(monkeypatch,tmp_path):
    app,obs,engine,hub,fir=init()
    try:
        # Test source snapshot validation independently of Phase FIR limits.
        fir.fir_mag_button.click()
        fir.compute()
        wait_fir(app,fir)
        assert fir.result is not None,fir.details.toPlainText()
        assert fir._proof_current()
        saved=fir._fir_fs
        changed=SimpleNamespace(hz=96000,modified_ns=1,size=123)
        monkeypatch.setattr(engine._saved_fs_cache,"get",lambda path:changed)
        fir.refresh_sources()
        assert fir.result is None
        assert fir._fir_fs==changed
        assert not fir.export_txt.isEnabled()
        assert not fir._proof_current()
        fir.compute()
        assert fir.result is None
        monkeypatch.setattr(engine._saved_fs_cache,"get",lambda path:saved)
        fir.refresh_sources()
        assert fir._fir_fs==saved
    finally:
        hub.close();app.processEvents()


def test_finished_fir_survives_one_transient_tick_and_fs_scan(monkeypatch):
    """A missed observer/config poll may hide preview, never delete taps."""
    app,obs,engine,hub,fir=init()
    try:
        for _ in range(3):
            tick(obs,{0})
        fir.refresh_sources()
        token=fir._verified_single()
        snap=SimpleNamespace(hz=48000,modified_ns=10,size=20)
        assert token is not None
        fir.fir_mode.setCurrentIndex(0)
        fir.taps.setCurrentIndex(fir.taps.findData(512))
        fir._fir_token=token
        fir._fir_fs=snap
        fir.result=SimpleNamespace(
            taps=np.ones(512), mode="mag", fs=snap.hz,
            source=Path(token[0]).stem, latency_ms=1.0)
        fir._approved=(token,fir._source_hash(token[0]),snap,512,
                       fir.fir_lf.value(),fir.fir_hf.value(),"mag")
        fir._approved_phase_plus=False
        fir._approved_window=getattr(obs,"hwnd",None)
        approved=fir._approved
        taps=fir.result.taps.copy()
        obs.single_tick=None
        monkeypatch.setattr(fir,"_fir_fs_snapshot",lambda:None)
        fir._fir_state=(approved[0],approved[2])
        fir.refresh_sources()
        assert fir.result is not None
        assert fir._approved==approved
        assert np.array_equal(fir.result.taps,taps)
        assert not fir.export_fir.isEnabled()
    finally:
        hub.close();app.processEvents()


def test_fir_actual_coefficient_prediction_and_float_wav(tmp_path):
    import scipy.signal
    f=np.linspace(20.,20000.,2500)
    h=np.ones_like(f,dtype=complex)
    coh=np.ones_like(f)
    from signal_tools_core_v813 import design_linear_phase_fir
    result=design_linear_phase_fir(f,h,coh,taps=2048,fs=48000,source="synthetic")
    assert np.isfinite(result.taps).all()
    assert np.allclose(result.taps,result.taps[::-1],atol=1e-10)
    # Compare on the SAME FFT bins, excluding near-zero linear-phase
    # Nyquist cancellation where dB interpolation is ill-conditioned.
    freqs,resp=scipy.signal.freqz(result.taps,worN=len(result.hz)-1,fs=48000)
    assert np.allclose(freqs,result.hz[:-1],atol=1e-12)
    predicted=20*np.log10(np.maximum(np.abs(resp),1e-12))
    accepted=(predicted>-55)&(result.actual_db[:-1]>-55)
    assert accepted.sum()>5000
    assert np.max(np.abs(result.actual_db[:-1][accepted]-predicted[accepted]))<1e-5
    wav=tmp_path/"fir2048.wav"
    save_fir_wav_float(wav,result)
    from scipy.io import wavfile
    fs,out=wavfile.read(wav)
    assert fs==48000 and out.dtype==np.float32 and len(out)==2048
    assert np.max(abs(out.astype(float)-result.taps))<1e-7


def test_fir_inflight_source_change_releases_compute_button():
    app,obs,engine,hub,fir=init()
    try:
        fir._pending_fir=(7,)
        fir.calculate.setEnabled(False)
        ticket=fir._serial
        tick(obs,{0,1})
        fir.refresh_sources()
        assert fir._serial>ticket
        assert fir._pending_fir is None
        assert fir.calculate.isEnabled()
        assert fir.result is None
        assert not fir.export_txt.isEnabled()
    finally:
        hub.close();app.processEvents()
