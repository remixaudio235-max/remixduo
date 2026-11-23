# -*- coding: utf-8 -*-
"""MagEq V0.7 invariants: 1 original + 1 new view; original never mutated."""
import hashlib,os
os.environ["QT_QPA_PLATFORM"]="offscreen"
from pathlib import Path
import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication
from trf_core import read_trf
from remix_autoeq_v05_adapter import design_remix_eq
from mageq_trace_v07 import create_mageq_trace
from native_eq_mag_v06 import build_state
from qa_fake_single import FakeSingle
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from test_v845_fir_one_trace import wait_fs

SRC=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"

def sample(name="4,8 ms delay-1.trf",target="House"):
    path=SRC/name
    if not path.exists():pytest.skip("Saved real Smaart fixture not available")
    trace=read_trf(path)
    result=design_remix_eq(trace.hz,trace.h,trace.coherence,
                           fs=48000,target=target,filters=8,lf=60,
                           hf=8000,boost=2,cut=-9,source=path.name)
    assert result.status=="PREVIEW_READY" and result.peqs
    return path,trace,result

def test_original_smaart_trace_and_file_never_change():
    path,t,eq=sample()
    source_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    f=t.hz.copy();h=t.h.copy();c=t.coherence.copy()
    m=create_mageq_trace(t.hz,t.h,t.coherence,eq.peqs,
          fs=48000,source_index=0,source_name=path.stem,revision=1)
    assert m.name=="MagEq ["+path.stem+"]"
    assert m.name!=path.stem and m.source_name==path.stem
    assert np.array_equal(t.hz,f) and np.array_equal(t.h,h) and np.array_equal(t.coherence,c)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source_sha
    assert np.max(np.abs(m.mageq_mag_db-m.original_mag_db))>.1
    for arr in (m.freq_hz,m.original_mag_db,m.mageq_mag_db,m.coherence):
        assert not arr.flags.writeable
        with pytest.raises(ValueError):arr[0]=123

def test_exactly_one_mageq_replaces_previous_overlay_not_original():
    path,t,eq=sample()
    a=build_state(t.hz,t.h,t.coherence,eq.peqs,fs=48000,
          source_index=0,source_name=path.stem,revision=1)
    b=build_state(t.hz,t.h,t.coherence,eq.peqs,fs=48000,
          source_index=0,source_name=path.stem,revision=2)
    assert a.name==b.name
    assert a.source_identity==b.source_identity
    assert np.array_equal(a.after_db,b.after_db)
    assert a.revision!=b.revision
    modified=t.h.copy();modified[len(modified)//4]*=1.01
    c=build_state(t.hz,modified,t.coherence,eq.peqs,fs=48000,
          source_index=0,source_name=path.stem,revision=3)
    assert c.source_identity!=b.source_identity

def test_mag_eq_is_not_a_sum_or_autophase_dsp_write():
    _,t,eq=sample()
    with pytest.raises(ValueError,match="SUM"):
        create_mageq_trace(t.hz,t.h,t.coherence,eq.peqs,
                           fs=48000,source_index=2,source_name="SUM",revision=1)
    with pytest.raises(ValueError,match="PEQ"):
        create_mageq_trace(t.hz,t.h,t.coherence,(),
                           fs=48000,source_index=0,source_name="T1",revision=1)

def test_auto_eq_gui_shows_one_source_one_mageq_and_ab_visibility():
    _,a,eq=sample()
    b=read_trf(SRC/"0 delay-1.trf")
    app=QApplication.instance() or QApplication([])
    eng=App(False);eng.timer.stop()
    eng.current_traces=(a,b)
    eng.current_pair=(str(a.path),str(b.path))
    eng.observer=FakeSingle(a.path)
    hub=ToolHub(eng);hub.timer.stop();hub.native_eq.timer.stop()
    try:
        hub.select("eq");app.processEvents()
        wait_fs(app,hub)
        assert hub.eq.plot.isHidden()
        assert hub.eq.mageq_toggle.isChecked()
        assert hub.eq.fs.currentData()==48000
        assert not hub.eq.fs.isEnabled()  # No manual Fs choice.
        assert hub.native_eq.source is None
        hub.eq.target.setCurrentText("House")
        hub.eq.source.setCurrentIndex(0)
        hub.eq.compute()
        import time
        start=time.monotonic()
        while hub.eq.result is None and time.monotonic()-start<16:
            app.processEvents();time.sleep(.01)
        assert hub.eq.result is not None
        assert hub.eq.result.status=="PREVIEW_READY"
        assert hub.native_eq.source is not None
        assert hub.native_eq.source.name.startswith("MagEq [")
        assert len(hub.native_eq.mageq_history)==1
        assert "Mag gốc:" in hub.eq.details.toPlainText()
        assert "MagEq:" in hub.eq.details.toPlainText()
        before=hub.native_eq.source
        hub.eq.mageq_toggle.setChecked(False)
        assert not hub.native_eq.enabled
        assert hub.native_eq.source is before
        hub.eq.mageq_toggle.setChecked(True)
        assert hub.native_eq.enabled
        # Selecting a different source must invalidate the old MagEq immediately.
        eng.observer.set_path(SRC/"0 delay-1.trf")
        hub.eq.refresh_sources()
        assert hub.native_eq.source is None
        assert hub.eq.result is None
        assert hub.native_eq.frame is None
        assert np.array_equal(a.h,read_trf(a.path).h)
    finally:
        hub.close()
        app.processEvents()
