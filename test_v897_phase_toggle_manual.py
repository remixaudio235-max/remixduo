"""V8.97: manual Phase+ checkbox (default OFF) and free taps, no auto selection.

Qt offscreen regression. The mock Smaart observer and source are read-only.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from test_v845_fir_one_trace import init,wait_fir


def test_manual_phase_checkbox_default_off_all_taps_and_proof_invalidation():
    app,observer,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        assert fir.fir_mode.currentData()=="phase"
        assert not fir.phase_plus.isChecked()
        assert not fir.phase_plus.isHidden()
        app.processEvents()
        assert fir.fir_mode.currentData()=="phase"
        assert not fir.phase_plus.isChecked()
        assert not fir.phase_plus.isHidden()
        assert fir.taps.isEnabled()
        for tap_count in (512,1024,2048,4096):
            fir.taps.setCurrentIndex(fir.taps.findData(tap_count))
            assert fir.taps.currentData()==tap_count
            assert fir.taps.isEnabled()
            assert not fir.phase_plus.isChecked()
        fir.taps.setCurrentIndex(fir.taps.findData(1024))
        fir.fir_lf.setValue(368)
        fir.fir_hf.setValue(3350)
        fir.compute()
        wait_fir(app,fir,timeout=20)
        assert fir.result is not None
        assert any(str(w).startswith("PREVIEW_ONLY:") for w in fir.result.warnings)
        assert "PREVIEW_ONLY" in fir.details.toPlainText()
        assert not fir.export_fir.isEnabled()
        fir.phase_plus.setChecked(True)
        assert fir.phase_plus.isChecked()
        assert fir.taps.currentData()==1024
        assert fir.taps.isEnabled()
        assert fir.result is None and fir._approved is None
        assert not fir.export_fir.isEnabled()
        fir.taps.setCurrentIndex(fir.taps.findData(2048))
        assert fir.taps.currentData()==2048
        assert fir.phase_plus.isChecked()
        fir.phase_plus.setChecked(False)
        assert not fir.phase_plus.isChecked()
        assert fir.taps.currentData()==2048
        assert fir.taps.isEnabled()
        fir.fir_mode.setCurrentIndex(0)
        assert fir.phase_plus.isHidden()
        assert not fir.phase_plus.isChecked()
    finally:
        hub.close()
        app.processEvents()
