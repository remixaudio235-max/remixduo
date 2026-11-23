"""Qt GUI must not allow exporting a Phase FIR that cannot resolve LF."""
import os,hashlib
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from test_v845_fir_one_trace import init,wait_fir

def test_gui_phase_512_35_188_holds_export_and_source_unchanged():
    app,obs,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        source=Path(obs.order[0])
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        fir.fir_mode.setCurrentIndex(1)  # phase mode
        fir.taps.setCurrentIndex(fir.taps.findData(512))
        fir.fir_lf.setValue(35)
        fir.fir_hf.setValue(188)
        app.processEvents()
        assert fir.fir_mode.currentData()=="phase"
        assert fir.taps.currentData()==512
        fir.compute()
        wait_fir(app,fir,timeout=10)
        assert fir.calculate.isEnabled()
        assert fir.result is not None
        assert any(str(w).startswith("PREVIEW_ONLY:") for w in fir.result.warnings)
        assert not fir.export_txt.isEnabled()
        assert not fir.export_wav.isEnabled()
        assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    finally:
        hub.close()
        app.processEvents()
