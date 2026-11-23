from pathlib import Path
from PyQt6.QtWidgets import QApplication,QCheckBox,QDoubleSpinBox
from trf_core import read_trf,auto_align
from positive_delay_route_v87 import route_candidate
from overlay_v7 import App

app=QApplication([])
w=App(demo=False)
w.timer.stop()
w.show()
app.processEvents()
root=Path(__file__).resolve().parent
data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
assert (w.width(),w.height())==(402,515)
assert not w.delay.isVisible() and not w.invert.isVisible()
assert not w.delay_route_label.isVisible()
for pair in (("SUb.trf","FULL.trf"),("4,8 ms delay-1.trf","0 delay-1.trf")):
    a,b=(read_trf(data/name) for name in pair)
    w.current_pair=(str(a.path),str(b.path))
    w.current_traces=(a,b)
    w.ref_choice.blockSignals(True);w.ref_choice.setCurrentIndex(0);w.ref_choice.blockSignals(False)
    w.delay.blockSignals(True);w.delay.setValue(0);w.delay.blockSignals(False)
    w.invert.blockSignals(True);w.invert.setChecked(False);w.invert.blockSignals(False)
    w._update_delay_route_label()
    w.lf.setValue(60);w.hf.setValue(200);w.recalc()
    expected=route_candidate(auto_align(a,b,lf=60,hf=200,max_delay_ms=180)[0])
    w.align()
    app.processEvents()
    assert w.ref_choice.currentIndex()==expected.reference_index
    assert abs(w.delay.value()-expected.delay_ms)<0.05
    assert w.invert.isChecked()==expected.invert_target
    assert not w.delay.isVisible() and not w.invert.isVisible()
    for i in range(2):
        val=w.delay.value() if i==expected.delay_target_index else 0.0
        polarity=("Đảo pha" if expected.invert_target else "Không đảo") if i==expected.delay_target_index else "Không đảo"
        assert w.trace_delay_static[i].text()==f"{val:.2f} ms",(i,w.trace_delay_static[i].text())
        assert w.trace_polarity_static[i].text()==polarity
        assert w.trace_delay_static[i].isVisible()
        assert w.trace_polarity_static[i].isVisible()
        assert isinstance(w.trace_delay_static[i],type(w.trace_name_labels[i]))
        assert isinstance(w.trace_polarity_static[i],type(w.trace_name_labels[i]))
        assert w.trace_grid.itemAtPosition(i,2).widget() is w.trace_delay_static[i]
        assert w.trace_grid.itemAtPosition(i,3).widget() is w.trace_polarity_static[i]
        for c in (w.trace_delay_static[i],w.trace_polarity_static[i]):
            pos=c.mapTo(w,c.rect().topLeft())
            assert 0<=pos.x() and pos.x()+c.width()<=w.width()+1
            assert 0<=pos.y() and pos.y()+c.height()<=w.height()+1
    print("READONLY_RESULT_PASS",pair,
          "T1",w.trace_delay_static[0].text(),w.trace_polarity_static[0].text(),
          "T2",w.trace_delay_static[1].text(),w.trace_polarity_static[1].text(),flush=True)
    if pair[0]=="SUb.trf":
        assert expected.delay_trace==1 and expected.invert_target
        assert w.grab().save(str(root/"V89_SUB_FULL_READONLY.png"))
    first=(tuple(x.text() for x in w.trace_delay_static),
           tuple(x.text() for x in w.trace_polarity_static))
    w.align()
    assert first==(tuple(x.text() for x in w.trace_delay_static),
                   tuple(x.text() for x in w.trace_polarity_static))
    print("REPEATED_AUTO_ALIGN_STABLE_PASS",flush=True)
# Internal values may change via solver, but never via an on-screen input.
w.ref_choice.setCurrentIndex(1-w.ref_choice.currentIndex())
w.delay.setValue(9.40)
w.invert.setChecked(True)
app.processEvents()
assert not w.delay.isVisible() and not w.invert.isVisible()
assert w.trace_delay_static[1-w._reference_index()].text()=="9.40 ms"
assert w.trace_polarity_static[1-w._reference_index()].text()=="Đảo pha"
print("INTERNAL_UPDATE_REFRESHES_STATIC_LABELS_PASS")
for i in range(w.tabs.count()):
    w.tabs.setCurrentIndex(i)
    app.processEvents()
    assert w.grab().save(str(root/f"V89_READONLY_TAB_{i}.png"))
w.close();app.processEvents()
print("V89_READONLY_GUI_ALL_PASS",flush=True)
