import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication,QWidget,QLabel
from PyQt6.QtCore import QRect
from overlay_v7 import App
from trf_core import read_trf
app=QApplication([])
w=App(demo=False)
w.timer.stop()
folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(folder/"4,8 ms delay-1.trf")
b=read_trf(folder/"0 delay-1.trf")
w.current_pair=(str(a.path),str(b.path))
w.current_traces=(a,b)
w.pair_label.setText("01  "+a.path.stem+"\n02  "+b.path.stem)
w.recalc()
w.align()
w.status.setText("Đã chọn 2 Trace · REF 1 cố định · SHIFT +4,80 ms")
w.tabs.setCurrentIndex(0)
app.processEvents()
root=Path(__file__).resolve().parent
for i in range(w.tabs.count()):
    w.tabs.setCurrentIndex(i)
    app.processEvents()
    fn=root/f"V85_REMIX_SIGNAL_TAB_{i}.png"
    ok=w.grab().save(str(fn))
    print("SNAPSHOT",i,fn,ok,flush=True)
w.tabs.setCurrentIndex(0)
app.processEvents()
print("ROOT_SIZE",w.width(),w.height())
widgets=("pair_label","phase_match_label","sum_ref_label","status","lf","hf",
         "delay","invert","solve","mag","phase","mag_smooth","phase_smooth",
         "mag_fit","mag_min","mag_max","phase_min","phase_max","axis_note",
         "phase_axis_note","mag_axis_note","tabs")
for attr in widgets:
    widget=getattr(w,attr)
    origin=widget.mapTo(w,widget.rect().topLeft())
    print("GEOMETRY",attr,"visible",widget.isVisible(),
          "x",origin.x(),"y",origin.y(),"size",widget.width(),widget.height())
    assert widget.width()>20 and widget.height()>5,(attr,"collapsed")
    if widget.isVisible():
        assert origin.x()>=0 and origin.x()+widget.width()<=w.width()+1,("X_OVERFLOW",attr)
        assert origin.y()>=0 and origin.y()+widget.height()<=w.height()+1,("Y_OVERFLOW",attr)
w.close()
app.processEvents()
print("V85_GUI_LAYOUT_TEST_PASS",flush=True)
