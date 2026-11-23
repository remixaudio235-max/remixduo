"""V8.118 FIR UX: no-improvement Phase FIR is HOLD; long names keep their
suffix; a setting changed mid-design explains why the result disappeared."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import pytest
import signal_tools_gui_v813 as tools
from signal_tools_gui_v813 import _middle_elide


@pytest.mark.parametrize("text,limit,out",[
    ("VIP 2 SKY SUB find 8,83-1",24,"VIP 2 SKY S… find 8,83-1"),
    ("short",24,"short"),
    ("abcdefghij",5,"ab…ij")])
def test_middle_elide_keeps_suffix(text,limit,out):
    got=_middle_elide(text,limit)
    assert got==out and len(got)<=limit


def test_phase_fir_min_improvement_gate_present():
    assert tools.FIR_PHASE_MIN_IMPROVEMENT_PCT==5.0
    src=open(tools.__file__,encoding="utf-8").read()
    fin=src.split("class FIRDialog",1)[1].split("def _finish",1)[1].split("        self.result=result",1)[0]
    assert "FIR_PHASE_MIN_IMPROVEMENT_PCT" in fin and "raise ValueError" in fin


def test_setting_change_mid_design_is_explained():
    from test_v845_fir_one_trace import init
    app,obs,engine,hub,fir=init()
    try:
        fir._pending_fir=(fir._serial+1,)
        fir.calculate.setEnabled(False)          # worker running
        fir.fir_lf.setValue(fir.fir_lf.value()+10)
        assert "đang tính" in fir.summary.text()
        assert fir.calculate.isEnabled()
    finally:
        hub.close();engine.close();app.processEvents()
