"""V8.6 compact UI acceptance (offscreen Qt, no Smaart audio I/O)."""
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from trf_core import read_trf

root=Path(__file__).resolve().parent
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
gui.show()
app.processEvents()
assert gui.size().width()==402 and gui.size().height()==510
hidden=("ref_choice","correction_target_label","phase_match_label",
        "sum_ref_label","roi_hint","lf","hf","status")
for name in hidden:
    item=getattr(gui,name)
    assert not item.isVisible(),("RED_REGION_VISIBLE",name)
    print("HIDDEN_RED_REGION_PASS",name,flush=True)
assert not gui.phase_match_card.isVisible()
for label in ("READ ONLY","REF CỐ ĐỊNH"):
    assert label not in [child.text() for child in gui.findChildren(type(gui.phase_match_label)) if child.isVisible()],label
visible=("pair_label","delay","invert","solve","tabs")
for name in visible:
    item=getattr(gui,name)
    assert item.isVisible(),("MISSING_PRIMARY_CONTROL",name)
    pos=item.mapTo(gui,item.rect().topLeft())
    assert 0<=pos.x() and 0<=pos.y(),(name,pos)
    assert pos.x()+item.width()<=gui.width()+1,(name,"x overflow",pos.x(),item.width())
    assert pos.y()+item.height()<=gui.height()+1,(name,"y overflow",pos.y(),item.height())
    print("VISIBLE_CONTROL_PASS",name,"rect",pos.x(),pos.y(),item.width(),item.height(),flush=True)
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(p/"4,8 ms delay-1.trf")
b=read_trf(p/"0 delay-1.trf")
gui.current_pair=(str(a.path),str(b.path))
gui.current_traces=(a,b)
gui.pair_label.setText("01  "+a.path.stem+"\n02  "+b.path.stem)
gui.recalc()
gui.align()
assert gui.last_solve and abs(gui.delay.value()-4.8)<.11
assert gui.current_sum is not None
assert gui.ref_choice.currentIndex()==0
assert gui.phase_match_label.text() and gui.sum_ref_label.text()
print("HIDDEN_PHASE_MATCH_STILL_UPDATED_PASS",gui.phase_match_label.text(),flush=True)
before=(gui.lf.value(),gui.hf.value())
gui.lf.setValue(72.0)
gui.hf.setValue(244.0)
app.processEvents()
assert abs(gui.lf.value()-72)<.01 and abs(gui.hf.value()-244)<.01
assert abs(gui.graph_phase.lf_hz-72)<.01 and abs(gui.graph_mag.hf_hz-244)<.01
print("HIDDEN_LF_HF_STILL_DRIVE_GRAPH_PASS",before,"->",gui.lf.value(),gui.hf.value(),flush=True)
for index in range(gui.tabs.count()):
    gui.tabs.setCurrentIndex(index)
    app.processEvents()
    file=root/f"REMIX_SIGNAL_V86_COMPACT_TAB_{index}.png"
    assert gui.grab().save(str(file))
    print("SCREENSHOT",str(file),flush=True)
gui.tabs.setCurrentIndex(0)
gui.close()
app.processEvents()
print("V86_COMPACT_QA_ALL_PASS",flush=True)
