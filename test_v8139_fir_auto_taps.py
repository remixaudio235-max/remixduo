import numpy as np
import pytest


def _measurement():
    freq = np.geomspace(20.0, 20_000.0, 600)
    phase = -2 * np.pi * freq * 0.001 + 0.8 * np.sin(np.log(freq) * 3)
    magnitude = np.power(10.0, 3.0 * np.sin(np.log(freq) * 2.0) / 20.0)
    return freq, magnitude * np.exp(1j * phase), np.zeros_like(freq)


def test_auto_taps_zero_coherence_returns_preview_only_phase():
    from signal_tools_gui_v813 import _fir_design_and_preview
    freq, transfer, coherence = _measurement()
    assert not np.any(coherence >= .65)
    result, preview = _fir_design_and_preview(
        freq, transfer, coherence, 0, 48_000, "trace", "digest", 1,
        60, 1000, "phase", False,
    )
    assert result.taps.size and preview.mode == "phase"
    assert any(str(w).startswith("PREVIEW_ONLY:") for w in result.warnings)


def test_fir_taps_control_defaults_to_auto():
    from test_v845_fir_one_trace import init

    app, observer, engine, hub, fir = init()
    try:
        assert fir.taps.itemData(0) == 0
        assert fir.taps.itemText(0) == "AUTO taps"
        assert fir.taps.currentData() == 0
    finally:
        hub.close()
        app.processEvents()


def test_auto_taps_flat_mag_returns_preview_only_after_all_candidates(monkeypatch):
    import signal_tools_gui_v813 as gui
    calls=[]
    original=gui.design_linear_phase_fir
    def counted(*args,**kwargs):
        calls.append(int(kwargs["taps"]))
        return original(*args,**kwargs)
    monkeypatch.setattr(gui,"design_linear_phase_fir",counted)
    freq=np.geomspace(20.,20_000.,600)
    transfer=np.ones_like(freq,dtype=complex)
    result,preview=gui._fir_design_and_preview(
        freq,transfer,np.ones_like(freq),0,48_000,
        "flat","digest",1,60,8000,"mag",False)
    assert calls==[512,1024,2048,4096]
    assert result.taps.size and preview.mode=="mag"
    assert any(str(w).startswith("PREVIEW_ONLY:") for w in result.warnings)
