"""V8.71 explicit V8 TRF import; no fake Smaart tick or DSP operation."""
import os,hashlib,shutil
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from unittest.mock import patch
import pytest
from PyQt6.QtWidgets import QApplication
from smaart_fs_sync_v841 import SavedSmaartFs
from test_v845_fir_one_trace import init,wait_fir
from test_v16_independent_one_tick import DATA
from signal_tools_gui_v813 import FIRDialog

def test_v8_manual_trf_design_export_without_tick(tmp_path,monkeypatch):
    sample=DATA/"0 delay-1.trf"
    assert sample.is_file()
    local=tmp_path/"verified_offline.trf"
    shutil.copy2(sample,local)
    original_sha=hashlib.sha256(local.read_bytes()).hexdigest()
    snap=SavedSmaartFs(48000,1,2)
    monkeypatch.setattr("signal_tools_gui_v813.read_saved_smaart_fs",
                        lambda path=None:snap)
    monkeypatch.setattr("smaart_runtime_paths_v868.running_major",lambda:8)
    app,obs,engine,hub,fir=init(one=False)
    fired=[]
    fir.preview_ready.connect(lambda obj:fired.append("overlay"))
    try:
        assert fir.source.currentData() is None
        assert fir.offline_button.text()=="Chọn TRF V8"
        assert not fir.export_txt.isEnabled()
        fir.set_offline_trf(local)
        assert fir._fir_fs==snap
        assert "OFFLINE" in fir.source.currentText()
        assert fir._verified_single() is not None
        assert fir.get_data()[0].size>50
        fir.fir_lf.setValue(200)
        fir.fir_hf.setValue(5000)
        fir.taps.setCurrentIndex(fir.taps.findData(1024))
        fir.compute()
        wait_fir(app,fir)
        assert fir.result is not None,fir.details.toPlainText()
        assert fir._proof_current()
        assert len(fir.result.taps)==1024
        assert fir.result.fs==48000
        assert fir.export_txt.isEnabled() and fir.export_wav.isEnabled()
        assert "OFFLINE" in fir.summary.text()
        assert fired==[], "Manual source must not present as native overlay"
        assert hashlib.sha256(local.read_bytes()).hexdigest()==original_sha
        from signal_tools_core_v813 import save_fir_wav_float
        path=tmp_path/"offline_fir.wav"
        save_fir_wav_float(path,fir.result)
        assert path.stat().st_size==44+4*1024
        # Changed file contents/stat invalidate all exports.
        local.write_bytes(local.read_bytes()+b"\n")
        assert not fir._proof_current()
        assert fir._verified_single() is None
        fir._refresh_export()
        assert not fir.export_txt.isEnabled() and not fir.export_wav.isEnabled()
    finally:
        hub.close()
        app.processEvents()

def test_v8_manual_source_rejected_on_v9(tmp_path,monkeypatch):
    snap=SavedSmaartFs(48000,1,2)
    monkeypatch.setattr("signal_tools_gui_v813.read_saved_smaart_fs",
                        lambda path=None:snap)
    monkeypatch.setattr("smaart_runtime_paths_v868.running_major",lambda:9)
    app=QApplication.instance() or QApplication([])
    dlg=FIRDialog(object())
    try:
        with pytest.raises(ValueError,match="Smaart 9"):
            dlg.set_offline_trf(DATA/"0 delay-1.trf")
        assert dlg._verified_single() is None
        assert not dlg.export_txt.isEnabled()
    finally:
        dlg._really_close=True
        dlg.close()
