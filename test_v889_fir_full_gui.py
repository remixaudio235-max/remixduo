"""V8.89 end-to-end FIR Qt interactions (fixture, no Smaart/audio writes)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from types import SimpleNamespace
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QFileDialog
from test_v845_fir_one_trace import init,wait_fir
from roi_markers_v73 import hz_to_x

PHASE=(252,84,1442,412)
MAG=(252,539,1442,412)


def test_fir_full_mag_phase_drag_design_export_switch_hide(tmp_path,monkeypatch):
    app,obs,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        engine.plot_layout=SimpleNamespace(phase=PHASE,mag=MAG)
        engine.overlay_positioned=True
        engine._apply_plot_layout()
        # Default is PHA; select MAG explicitly for this MAG->PHA test.
        fir.fir_mag_button.click()
        fir.taps.setCurrentIndex(fir.taps.findData(1024))
        hub.select("fir")
        app.processEvents()
        phase_before=(engine.lf.value(),engine.hf.value())
        assert engine.graph_mag.fir_roi_active
        assert all(g.isVisible() for g in engine.fir_roi_line_grips.values())

        # FIR magnitude: native drag -> spin boxes -> worker -> export buttons.
        engine.on_fir_roi_drag("LF",hz_to_x(90,MAG[0],MAG[2]))
        engine.on_fir_roi_drag("HF",hz_to_x(12000,MAG[0],MAG[2]))
        assert abs(fir.fir_lf.value()-90)<2
        assert abs(fir.fir_hf.value()-12000)<10
        assert (engine.lf.value(),engine.hf.value())==phase_before
        QTest.mouseClick(fir.calculate,Qt.MouseButton.LeftButton)
        wait_fir(app,fir)
        assert fir.result is not None,fir.details.toPlainText()
        assert fir.result.mode=="mag"
        assert len(fir.result.taps)==1024
        assert fir.export_txt.isEnabled() and fir.export_wav.isEnabled()
        txt=tmp_path/"mag_fir.txt";wav=tmp_path/"mag_fir.wav"
        monkeypatch.setattr(QFileDialog,"getSaveFileName",
            lambda *args,**kwargs:(str(wav if "WAV" in args[1] else txt),""))
        QTest.mouseClick(fir.export_txt,Qt.MouseButton.LeftButton)
        QTest.mouseClick(fir.export_wav,Qt.MouseButton.LeftButton)
        assert txt.exists() and wav.exists()

        # The current FIR must be invalidated immediately on a mode change.
        fir.fir_mode.setCurrentIndex(1)
        app.processEvents()
        assert fir.result is None and fir._approved is None
        assert not fir.export_txt.isEnabled() and not fir.export_wav.isEnabled()
        assert engine.graph_phase.fir_roi_active
        assert engine.fir_roi_markers["LF"].y()==PHASE[1]+5
        engine.on_fir_roi_drag("LF",hz_to_x(368,PHASE[0],PHASE[2]))
        engine.on_fir_roi_drag("HF",hz_to_x(3350,PHASE[0],PHASE[2]))
        assert abs(fir.fir_lf.value()-368)<2
        assert abs(fir.fir_hf.value()-3350)<10
        QTest.mouseClick(fir.calculate,Qt.MouseButton.LeftButton)
        wait_fir(app,fir)
        assert fir.result is not None,fir.details.toPlainText()
        assert fir.result.mode=="phase"
        assert np.isfinite(fir.result.taps).all()
        assert len(fir.result.taps)==1024
        assert fir._approved_phase_plus is False
        assert not fir.phase_plus.isChecked()
        assert not fir.phase_plus.isHidden()  # parent may be hidden in offscreen QA
        assert fir.export_wav.isEnabled()
        wav_phase=tmp_path/"phase_fir.wav"
        monkeypatch.setattr(QFileDialog,"getSaveFileName",
                            lambda *args,**kwargs:(str(wav_phase),""))
        QTest.mouseClick(fir.export_wav,Qt.MouseButton.LeftButton)
        assert wav_phase.exists()
        assert (engine.lf.value(),engine.hf.value())==phase_before

        # Switching tabs/explicit HIDE leaves only the Smaart graph interactive.
        hub.select("phase")
        app.processEvents()
        assert not any(g.isVisible() for g in engine.fir_roi_line_grips.values())
        hub.select("fir")
        app.processEvents()
        assert all(g.isVisible() for g in engine.fir_roi_line_grips.values())
        hub.hide_workspace()
        app.processEvents()
        assert not engine.graph_phase.isVisible()
        assert not any(g.isVisible() for g in engine.fir_roi_line_grips.values())
    finally:
        hub.close()
        engine.managed_mode=False
        engine.close()
        app.processEvents()
