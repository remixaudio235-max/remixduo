"""RemiX Signal V8.8 inline Delay/phase UI regression and real trace case."""
from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import QApplication
from trf_core import read_trf,auto_align
from positive_delay_route_v87 import route_candidate
from overlay_v7 import App

data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
root=Path(__file__).resolve().parent
app=QApplication([])
w=App(demo=False)
w.timer.stop()
w.show()
app.processEvents()
assert (w.width(),w.height())==(402,515),(w.width(),w.height())
assert not w.pair_label.isVisible()
assert not w.delay_route_label.isVisible()
assert w.delay.isVisible() and w.invert.isVisible()
assert w._inline_target_index==1
for pair in (("SUb.trf","FULL.trf"),("4,8 ms delay-1.trf","0 delay-1.trf")):
    a,b=(read_trf(data/filename) for filename in pair)
    w.current_pair=(str(a.path),str(b.path))
    w.current_traces=(a,b)
    w.ref_choice.blockSignals(True)
    w.ref_choice.setCurrentIndex(0)
    w.ref_choice.blockSignals(False)
    w.delay.blockSignals(True)
    w.delay.setValue(0)
    w.delay.blockSignals(False)
    w.invert.blockSignals(True)
    w.invert.setChecked(False)
    w.invert.blockSignals(False)
    w._update_delay_route_label()
    w.lf.setValue(60)
    w.hf.setValue(200)
    w.recalc()
    result=auto_align(a,b,lf=60,hf=200,max_delay_ms=180)
    expected=route_candidate(result[0])
    w.align()
    app.processEvents()
    assert w.ref_choice.currentIndex()==expected.reference_index
    assert w._inline_target_index==expected.delay_target_index
    assert abs(w.delay.value()-expected.delay_ms)<.05
    assert w.invert.isChecked()==expected.invert_target
    assert w.invert.text()==("Đảo pha" if expected.invert_target else "Không đảo")
    assert w.trace_delay_static[expected.reference_index].isVisible()
    assert not w.trace_delay_static[expected.delay_target_index].isVisible()
    assert w.trace_polarity_static[expected.reference_index].text()=="Không đảo"
    assert f"{expected.delay_ms:.2f}" in w.delay.text()
    assert w.trace_grid.itemAtPosition(expected.delay_target_index,2).widget() is w.delay
    assert w.trace_grid.itemAtPosition(expected.delay_target_index,3).widget() is w.invert
    trace_names=[label.text() for label in w.trace_name_labels]
    print("PAIR",pair,"NAMES",trace_names,"TARGET",expected.delay_trace,
          "REF",expected.reference_trace,"DELAY",w.delay.text(),
          "INV",w.invert.text(),flush=True)
    for control in (*w.trace_name_labels,w.delay,w.invert,w.solve):
        top=control.mapTo(w,control.rect().topLeft())
        assert 0<=top.x() and 0<=top.y(),(control,top)
        assert top.x()+control.width()<=w.width()+2,(control,top)
        assert top.y()+control.height()<=w.height()+2,(control,top)
    old=(w._inline_target_index,w.delay.value(),w.invert.isChecked())
    w.align()
    assert old==(w._inline_target_index,w.delay.value(),w.invert.isChecked())
    assert w.trace_grid.itemAtPosition(expected.delay_target_index,2).widget() is w.delay
    print("REPEATED_AUTO_ALIGN_NO_WRONG_ROW_PASS",pair,flush=True)
    if pair[0]=="SUb.trf":
        assert expected.delay_trace==1 and expected.invert_target
        assert w.grab().save(str(root/"V88_SUB_FULL_INLINE.png"))
# Flip reference in GUI: widgets must move to the other row, no DSP recalculation from relocation.
current=w._inline_target_index
w.ref_choice.setCurrentIndex(1-w.ref_choice.currentIndex())
app.processEvents()
assert w._inline_target_index==1-current
assert w.trace_grid.itemAtPosition(1-current,2).widget() is w.delay
assert w.trace_grid.itemAtPosition(1-current,3).widget() is w.invert
print("REF_SWAP_RELOCATES_BOTH_CONTROLS_PASS")
# Manual changes update on-row phase status on same target:
w.invert.setChecked(False)
assert w.invert.text()=="Không đảo"
w.invert.setChecked(True)
assert w.invert.text()=="Đảo pha"
w.delay.setValue(9.4)
assert "9.40" in w.delay.text()
assert "9.40" in w.delay_route_label.text()
print("MANUAL_DELAY_AND_PHASE_STATUS_UPDATE_PASS")
for i in range(w.tabs.count()):
    w.tabs.setCurrentIndex(i)
    app.processEvents()
    assert w.grab().save(str(root/f"V88_INLINE_TAB_{i}.png"))
w.close();app.processEvents()
print("V88_INLINE_GUI_ALL_QA_PASS",flush=True)
