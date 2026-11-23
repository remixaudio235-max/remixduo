"""Qt-only FIR sidebar smoke test. Never starts Smaart or audio."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PyQt6.QtWidgets import QApplication
from signal_tools_gui_v813 import FIRDialog
from remix_layout_v856 import style_fir

def test_fir_hidden_range_keeps_computation_bindings():
    app=QApplication.instance() or QApplication([])
    fir=FIRDialog(object())
    try:
        style_fir(fir,fir._action_row)
        fir.show(); app.processEvents()
        assert fir.fir_lf.value()==500
        assert fir.fir_hf.value()==2500
        assert fir.main.indexOf(fir._taps_row)>=0
        assert fir._taps_row.indexOf(fir.taps_label)==0
        assert fir._taps_row.indexOf(fir.taps)==1
        assert fir.taps_label.geometry().right()<fir.taps.geometry().left()
        # Hidden LF/HF overlay controls remain bound, but are deliberately
        # not part of the visible tap/mode layout order.
        assert fir.main.indexOf(fir.fir_range_label)>=0
        assert fir.main.indexOf(fir.overlay_status)>=0
        assert fir.height()>=fir.main.minimumSize().height()
        assert fir.dsp_profile.isHidden()
        assert fir.fir_range_label.isHidden()
        assert fir.fir_lf.isHidden() and fir.fir_hf.isHidden()
        assert fir.overlay_status.isHidden() and fir.fs.isHidden()
        assert fir._ux_sections[2].isHidden()
        serial=fir._serial
        fir.fir_lf.setValue(210)
        fir.fir_hf.setValue(18000)
        assert fir._serial>serial
        assert fir.fir_lf.value()==210 and fir.fir_hf.value()==18000
    finally:
        fir._really_close=True
        fir.close()
