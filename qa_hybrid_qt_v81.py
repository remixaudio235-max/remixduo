from pathlib import Path
from types import SimpleNamespace
from PyQt6.QtWidgets import QApplication
from trf_core import read_trf
from native_fast_pan_v81 import PanFrame
from fast_phase_y_v80 import FastFitResult
from phase_axis_absolute_v79 import AxisFit
from overlay_v7 import App
import numpy as np,win32gui,time

root=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(root/"4,8 ms delay-1.trf")
b=read_trf(root/"0 delay-1.trf")
app=QApplication([])
w=App(demo=False)
w.timer.stop()
h=win32gui.FindWindow(None,"Smaart Suite")
rect=(252,112,1442,398)
w.current_pair=(str(a.path),str(b.path))
w.current_traces=(a,b)
w.recalc()
w.delay.setValue(4.8)
w.plot_hwnd=h
w.plot_layout=SimpleNamespace(phase=rect,mag=(252,553,1442,398))
w._apply_plot_layout()
sum_before=w.current_sum
delay=w.delay.value()
percent=w.phase_match_label.text()
delta=w.sum_ref_label.text()
key=(h,rect,tuple(w.current_pair),0)
top=w.graph_phase.y_max
times=[]
for shift in (2,3,4,-8,-1,12,1,5):
    now=time.monotonic()
    frame=PanFrame(float(shift),.95,True,"test",7.2,now)
    start=time.perf_counter()
    w.on_native_fast_pan((key,frame))
    app.processEvents()
    elapsed=(time.perf_counter()-start)*1000
    times.append(elapsed)
    top += shift*360/398
    assert abs(w.graph_phase.y_max-top)<1e-6,(shift,w.graph_phase.y_max,top)
    assert w.current_sum is sum_before
    assert w.delay.value()==delay
    assert w.phase_match_label.text()==percent
    assert w.sum_ref_label.text()==delta
print("FAST_PAN_RENDER_PASS",len(times),"p95 ms",np.percentile(times,95),
      "values",np.round(times,2).tolist(),flush=True)
# Skip late absolute anchor while dragging.
w.on_absolute_phase_axis((key,FastFitResult(
    AxisFit(300,-60,.95,.3,200,True,"QA"),150,"printwindow",time.monotonic())))
assert abs(w.graph_phase.y_max-top)<1e-6
print("ABSOLUTE_DURING_DRAG_IGNORED_PASS",flush=True)
# Once stopped, absolute calibration can correct drift.
w.pan_last_move=time.monotonic()-2
w.on_absolute_phase_axis((key,FastFitResult(
    AxisFit(115,-245,.96,.3,200,True,"QA"),40,"gdi",time.monotonic())))
assert w.graph_phase.y_max==115
assert w.current_sum is sum_before
print("IDLE_ABSOLUTE_DRIFT_CORRECTION_PASS",flush=True)
w.ref_choice.setCurrentIndex(1)
new_top=w.graph_phase.y_max
w.on_native_fast_pan((key,PanFrame(25,.96,True,"old REF",5,time.monotonic())))
assert w.graph_phase.y_max==new_top
print("REF_OLD_FAST_FRAME_IGNORED_PASS",flush=True)
w.close();app.processEvents()
print("V81_HYBRID_QT_QA_ALL_PASS",flush=True)
