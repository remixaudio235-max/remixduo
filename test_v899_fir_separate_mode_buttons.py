"""V8.99: two exclusive FIR mode buttons + visible 'Chọn Taps' label.

GUI only; uses existing saved QA TRF and never captures audio or writes DSP.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from test_v845_fir_one_trace import init,wait_fir


def test_fir_two_mode_buttons_keep_internal_mode_and_phaseplus_manual():
    app,obs,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        hub.select("fir")
        hub.dock.show()
        app.processEvents()
        assert fir.taps_label.text()=="Chọn Taps"
        assert not fir.taps_label.isHidden()
        assert not fir.taps.isHidden()
        assert fir.taps.currentData()==0 and fir.taps.currentText()=="AUTO taps"
        assert fir.taps.isEnabled()
        assert fir.fir_mode.isHidden()    # compatibility state, not a visible selector
        assert [fir.fir_mag_button.text(),fir.fir_phase_button.text()]==[
            "FIR MAG","FIR PHA"]
        assert fir.fir_mag_button.isCheckable()
        assert fir.fir_phase_button.isCheckable()
        assert not fir.fir_mag_button.isHidden()
        assert not fir.fir_phase_button.isHidden()
        assert not fir.fir_mag_button.isChecked()
        assert fir.fir_phase_button.isChecked()
        assert fir.fir_mode.currentData()=="phase"
        assert not fir.phase_plus.isChecked() and not fir.phase_plus.isHidden()
        # Explicit MAG selection for testing legacy magnitude export.
        fir.fir_mag_button.click()
        assert fir.fir_mode.currentData()=="mag"
        assert fir.phase_plus.isHidden()
        assert fir.calculate.text()=="TẠO FIR"
        assert fir.calculate.receivers(fir.calculate.clicked)>=1
        assert fir.export_fir.text()=="XUẤT FIR"
        fir.compute()
        wait_fir(app,fir)
        assert fir.result is not None
        assert fir.result.mode=="mag"
        assert fir.export_fir.isEnabled()

        fir.fir_phase_button.click()
        app.processEvents()
        assert fir.fir_mode.currentData()=="phase"
        assert fir.fir_phase_button.isChecked()
        assert not fir.fir_mag_button.isChecked()
        assert not fir.phase_plus.isChecked()
        assert not fir.phase_plus.isHidden()
        assert fir.result is None and not fir.export_fir.isEnabled()
        # User can still select arbitrary taps independently.
        fir.taps.setCurrentIndex(fir.taps.findData(2048))
        assert fir.taps.currentData()==2048 and fir.taps.isEnabled()
        fir.phase_plus.setChecked(True)
        assert fir.taps.currentData()==2048
        assert fir.phase_plus.isChecked()
        fir.fir_mag_button.click()
        app.processEvents()
        assert fir.fir_mode.currentData()=="mag"
        assert fir.fir_mag_button.isChecked()
        assert not fir.fir_phase_button.isChecked()
        assert fir.phase_plus.isHidden()
        assert fir.taps.currentData()==2048
        # Programmatic integrations remain synchronized with the two buttons.
        fir.fir_mode.setCurrentIndex(1)
        assert fir.fir_phase_button.isChecked()
        assert not fir.fir_mag_button.isChecked()
        assert not fir.phase_plus.isHidden()
    finally:
        hub.close()
        app.processEvents()
