from pathlib import Path
import time,numpy as np,win32gui
from PIL import Image
from PyQt6.QtWidgets import QApplication
from phase_axis_absolute_v79 import fit_ref_phase_axis,AxisFit
from fast_phase_y_v80 import capture_fit_fast,FastFitResult
from trf_core import read_trf
from plot_geometry_v7 import locate_plots
from overlay_v7 import App
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(p/"4,8 ms delay-1.trf")
b=read_trf(p/"TUNNINNGGG-8.trf")
hwnd=win32gui.FindWindow(None,"Smaart Suite")
rect=(252,112,1442,398)
# GDI direct image from previously captured Smaart original is phase-validated.
root=Path(__file__).resolve().parent
im=Image.open(root.parent/"windows_v7_8_PASSIVE_Y_QA"/"V78_NATIVE_PHASE_AXES.png")
x,y,w,h=rect
cropped=im
fit=fit_ref_phase_axis(cropped,(0,0,w,h),(0,0,w,h),a,b,center_top=121)
assert fit.accepted,(fit,im.size)
print("GDI_STYLE_OVERLAY_MASK_ACCEPTED",fit)
# Current PrintWindow fallback must remain valid if GDI desktop obscured.
fast=capture_fit_fast(hwnd,rect,a,b,center_top=121)
assert isinstance(fast,FastFitResult),fast
print("FAST_CAPTURE_FALLBACK_PASS",fast.mode,round(fast.elapsed_ms,1))
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
gui.current_pair=(str(a.path),str(b.path))
gui.current_traces=(a,b)
gui.recalc()
gui.delay.setValue(4.8)
gui.plot_hwnd=hwnd
from types import SimpleNamespace
gui.plot_layout=SimpleNamespace(phase=rect,mag=(252,553,1442,398))
gui._apply_plot_layout()
base_sum=gui.current_sum
base_delay=gui.delay.value()
base_match=gui.phase_match_label.text()
base_delta=gui.sum_ref_label.text()
k=(hwnd,rect,tuple(gui.current_pair),0)
now=time.monotonic()
sequence=[80,95,110,126,145,160,169,205]
t=[]
for top in sequence:
 obj=FastFitResult(AxisFit(top,top-360,.96,.30,207,True,"QA"),21.0,
                   "gdi",time.monotonic())
 t0=time.perf_counter()
 gui.on_absolute_phase_axis((k,obj))
 app.processEvents()
 t.append((time.perf_counter()-t0)*1000)
 assert gui.graph_phase.y_max==top,(top,gui.graph_phase.y_max)
 assert gui.current_sum is base_sum
 assert gui.delay.value()==base_delay
 assert gui.phase_match_label.text()==base_match
 assert gui.sum_ref_label.text()==base_delta
 assert gui.graph_phase.y_min==top-360
 print("FAST_FRAME",top,round(t[-1],2),"ms")
assert gui.axis_accepted>=len(sequence)
# Ignore stale result from old REF.
gui.ref_choice.setCurrentIndex(1)
after_ref=gui.graph_phase.y_max
gui.on_absolute_phase_axis((k,FastFitResult(AxisFit(240,-120,.98,.2,200,True,"stale"),20,"gdi",time.monotonic())))
assert gui.graph_phase.y_max==after_ref
print("FAST_REF_STALE_RESULT_DROPPED")
# Drop frames older than 180ms.
k2=(hwnd,rect,tuple(gui.current_pair),1)
gui.on_absolute_phase_axis((k2,FastFitResult(AxisFit(256,-104,.95,.2,200,True,"stale"),220,"gdi",time.monotonic()-.25)))
assert gui.graph_phase.y_max==after_ref
print("FAST_LATE_RESULT_DROPPED")
gui.close();app.processEvents()
print("FAST_GUI_FRAME_MS",t,"P95",round(float(np.percentile(t,95)),2))
print("V80_FAST_QA_PASS")
