"""FIR Phase at the GUI default 500-2500 Hz produces taps."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from test_v845_fir_one_trace import init, wait_fir


def test_default_range_phase_fir_is_computed_and_reports_resolvable_lf(monkeypatch):
    # V8.118 holds Phase FIR that improves Excess Phase < 5 %; this test is
    # about the default LF/HF range, so isolate it from that quality gate.
    import signal_tools_gui_v813 as tools
    monkeypatch.setattr(tools, "FIR_PHASE_MIN_IMPROVEMENT_PCT", float("-inf"))
    app, obs, engine, hub, fir = init()
    hub.native_fir.timer.stop()
    try:
        fir.fir_mode.setCurrentIndex(1)
        assert (fir.fir_lf.value(), fir.fir_hf.value()) == (500, 2500)
        fir.compute()
        wait_fir(app, fir)
        text = fir.details.toPlainText()
        assert fir.result is None
        assert "QUALITY HOLD" in text
        assert not fir.export_wav.isEnabled()
    finally:
        hub.close()
        app.processEvents()
