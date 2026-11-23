"""Offscreen Qt screenshot and geometry QA for Smaart micro sidebar."""
from pathlib import Path
from PyQt6.QtWidgets import QApplication,QLabel,QCheckBox,QDoubleSpinBox
from overlay_v7 import App
from trf_core import read_trf,auto_align
from positive_delay_route_v87 import route_candidate
from plot_geometry_v7 import locate_plots
import win32gui
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
app=QApplication([])
w=App(demo=False)
w.timer.stop()
w.show()
app.processEvents()
assert w.width()==205 and w.height()==550,(w.width(),w.height())
assert len(w.trace_compact_result)==2
for t in w.trace_compact_result:
    assert isinstance(t,QLabel)
    assert t.isVisible()
assert not w.delay.isVisible() and not w.invert.isVisible()
for names in (("SUb.trf","FULL.trf"),
              ("4,8 ms delay-1.trf","0 delay-1.trf")):
    a,b=(read_trf(p/name) for name in names)
    w.current_pair=(str(a.path),str(b.path))
    w.current_traces=(a,b)
    w.ref_choice.blockSignals(True);w.ref_choice.setCurrentIndex(0);w.ref_choice.blockSignals(False)
    w.delay.blockSignals(True);w.delay.setValue(0);w.delay.blockSignals(False)
    w.invert.blockSignals(True);w.invert.setChecked(False);w.invert.blockSignals(False)
    w._update_delay_route_label()
    w.lf.setValue(60);w.hf.setValue(200);w.recalc()
    expected=route_candidate(auto_align(a,b,lf=60,hf=200,max_delay_ms=180)[0])
    w.align();app.processEvents()
    assert w.ref_choice.currentIndex()==expected.reference_index
    assert abs(w.delay.value()-expected.delay_ms)<0.06
    for i in range(2):
        delay=w.delay.value() if i==expected.delay_target_index else 0.
        state="Đảo pha" if (i==expected.delay_target_index and w.invert.isChecked()) else "Không đảo"
        assert w.trace_compact_result[i].text()==f"Delay {delay:.2f}ms · {state}"
    print("TRACE_PAIR_PASS",names,[x.text() for x in w.trace_compact_result],flush=True)
    before=[x.text() for x in w.trace_compact_result]
    w.align();app.processEvents()
    assert before==[x.text() for x in w.trace_compact_result]
    if names[0]=="SUb.trf":
        assert w.grab().save(str(Path(__file__).parent/"V810_MICRO_SUB_FULL.png"))
for tab in range(w.tabs.count()):
    w.tabs.setCurrentIndex(tab);app.processEvents()
    fn=Path(__file__).parent/f"V810_MICRO_TAB_{tab}.png"
    assert w.grab().save(str(fn))
    for child in w.findChildren(QLabel)+w.findChildren(QDoubleSpinBox)+w.findChildren(QCheckBox):
        if not child.isVisible() or child is w:
            continue
        top=child.mapTo(w,child.rect().topLeft())
        # skip overlays or plot widgets owned as top-level windows
        if top.x()>=0 and top.y()>=0:
            if top.x()+child.width()>w.width()+2 or top.y()+child.height()>w.height()+2:
                raise AssertionError(("VISIBLE_OVERFLOW",tab,type(child).__name__,child.objectName(),child.text() if hasattr(child,"text") else "",top.x(),top.y(),child.width(),child.height()))
    print("PANEL_BOUNDARY_PASS",tab,w.tabs.tabText(tab),flush=True)
h=win32gui.FindWindow(None,"Smaart Suite")
if h:
    rect=win32gui.GetWindowRect(h)
    geo=locate_plots(h)
    intended_left=rect[2]-205-3
    mag_right=geo.mag[0]+geo.mag[2]
    phase_right=geo.phase[0]+geo.phase[2]
    print("SMAART_PANEL_POSITION",rect,"LEFT",intended_left,
          "PHASE_RIGHT",phase_right,"MAG_RIGHT",mag_right,flush=True)
    assert intended_left>=max(phase_right,mag_right),("PANEL_STILL_OVER_PLOT",intended_left,phase_right,mag_right)
w.close();app.processEvents()
print("V810_MICRO_UI_QA_ALL_PASS",flush=True)
