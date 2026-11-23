"""V8.101 FIR default PHA / manual Phase+ and compact fixed UI order."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from test_v845_fir_one_trace import init,wait_fir


def test_first_open_defaults_phase_with_compact_order_and_manual_phaseplus():
    app,obs,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        hub.select("fir")
        hub.dock.show()
        app.processEvents()
        assert fir.fir_mode.currentData()=="phase"
        assert fir.fir_phase_button.isChecked()
        assert not fir.fir_mag_button.isChecked()
        assert fir.fir_mode.isHidden()
        assert not fir.phase_plus.isChecked()
        assert not fir.phase_plus.isHidden()
        assert fir.taps.currentData()==0 and fir.taps.currentText()=="AUTO taps"
        assert fir.taps.isEnabled()
        assert fir.taps_label.text()=="Chọn Taps"
        assert not fir.taps_label.isHidden()
        assert fir.calculate.text()=="TẠO FIR"
        assert fir.export_fir.text()=="XUẤT FIR"
        layout=fir.main
        taps_row=layout.indexOf(fir._taps_row)
        phase_plus=layout.indexOf(fir.phase_plus)
        modes=layout.indexOf(fir._fir_mode_row)
        actions=layout.indexOf(fir._action_row)
        assert 0<=taps_row<phase_plus<modes<actions
        assert layout.indexOf(fir.taps_label)==-1
        assert layout.indexOf(fir.taps)==-1
        assert fir._taps_row.indexOf(fir.taps_label)==0
        assert fir._taps_row.indexOf(fir.taps)==1
        assert fir._action_row.indexOf(fir.calculate)==0
        assert fir._action_row.indexOf(fir.export_fir)==1
        assert fir._fir_actions_layout is fir._action_row
        assert fir.taps_label.height()==16
        assert fir.taps_label.width()==67
        assert fir.height()<=380
        # 1 row / 2 columns: label left, taps combobox right.
        assert fir.taps_label.geometry().right()<fir.taps.geometry().left()
        assert abs(fir.taps_label.geometry().center().y()-
                   fir.taps.geometry().center().y())<=2
        # Pixel-geometry acceptance on the real 205px Smaart dock:
        # controls form one dense vertical stack without empty label space,
        # and the two actions appear side-by-side in a single row.
        stack=[fir.taps,fir.phase_plus,
               fir.fir_mag_button,fir.calculate]
        for previous,following in zip(stack,stack[1:]):
            gap=following.geometry().top()-previous.geometry().bottom()-1
            assert 0<=gap<=12,(previous.objectName(),following.objectName(),gap)
        assert fir.calculate.geometry().top()==fir.export_fir.geometry().top()
        assert fir.calculate.geometry().height()==fir.export_fir.geometry().height()
        assert fir.calculate.geometry().right()<fir.export_fir.geometry().left()
        assert not fir.summary.isHidden() and fir.details.isHidden()
        assert 40<=fir.summary.maximumHeight()<=78
        assert fir.offline_button.isHidden() and fir.offline_clear.isHidden()
        assert fir.fir_lf.isHidden() and fir.fir_hf.isHidden()

        # Changing mode/taps must not silently activate Phase+ or auto-compute.
        fir.fir_mag_button.click()
        assert fir.fir_mode.currentData()=="mag"
        assert fir.phase_plus.isHidden()
        fir.fir_phase_button.click()
        assert fir.fir_mode.currentData()=="phase"
        assert not fir.phase_plus.isChecked()
        assert fir.fir_phase_button.isChecked()
        assert fir.taps.currentData()==0
        fir.taps.setCurrentIndex(fir.taps.findData(2048))
        assert fir.taps.currentData()==2048 and fir.taps.isEnabled()
        fir.phase_plus.setChecked(True)
        assert fir.phase_plus.isChecked() and fir.taps.currentData()==2048
        fir.phase_plus.setChecked(False)
        assert not fir.phase_plus.isChecked()
        assert fir.taps.currentData()==2048
        assert fir.result is None and not fir.export_fir.isEnabled()
    finally:
        hub.close()
        app.processEvents()
