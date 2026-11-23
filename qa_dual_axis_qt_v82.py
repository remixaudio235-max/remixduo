from pathlib import Path
from types import SimpleNamespace
import time,numpy as np,win32gui
from PyQt6.QtWidgets import QApplication
from trf_core import read_trf
from native_fast_pan_v81 import PanFrame
from native_dual_y_v82 import DualPanResult
from overlay_v7 import App
folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(folder/name) for name in ("4,8 ms delay-1.trf","0 delay-1.trf"))
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
hwnd=win32gui.FindWindow(None,"Smaart Suite")
phase_rect=(252,112,1442,398)
mag_rect=(252,553,1442,398)
gui.current_pair=(str(a.path),str(b.path))
gui.current_traces=(a,b)
gui.recalc()
gui.delay.setValue(4.8)
gui.plot_hwnd=hwnd
gui.plot_layout=SimpleNamespace(phase=phase_rect,mag=mag_rect)
gui._apply_plot_layout()
old_sum=gui.current_sum
old_delay=gui.delay.value()
old_percent=gui.phase_match_label.text()
old_delta=gui.sum_ref_label.text()
old_offset=gui.graph_mag.display_offset_db
phase_y=(gui.graph_phase.y_min,gui.graph_phase.y_max)
mag_y=(gui.graph_mag.y_min,gui.graph_mag.y_max)
key=(hwnd,phase_rect,mag_rect,tuple(gui.current_pair),0)
def event(phase=0,mag=0):
 now=time.monotonic()
 def fr(d):return PanFrame(float(d),.96,True,"qa",8.0,now)
 gui.on_native_dual_pan((key,DualPanResult(fr(phase),fr(mag))))
 app.processEvents()
 print("DUAL_EVENT",phase,mag,"MAG_RANGE",gui.graph_mag.y_min,gui.graph_mag.y_max,
       "PH_RANGE",gui.graph_phase.y_min,gui.graph_phase.y_max,flush=True)
event(mag=8)
assert (gui.graph_phase.y_min,gui.graph_phase.y_max)==phase_y
expected=8*(mag_y[1]-mag_y[0])/mag_rect[3]
assert abs(gui.graph_mag.y_min-mag_y[0]-expected)<1e-7
assert abs(gui.graph_mag.y_max-mag_y[1]-expected)<1e-7
print("MAG_INDEPENDENT_OF_PHASE_PASS")
mag_before=(gui.graph_mag.y_min,gui.graph_mag.y_max)
event(phase=-7)
assert (gui.graph_mag.y_min,gui.graph_mag.y_max)==mag_before
assert gui.graph_phase.y_min<phase_y[0]
print("PHASE_INDEPENDENT_OF_MAG_PASS")
times=[]
for shift in (-3,-1,1,4,6,-10,9):
 t=time.perf_counter()
 event(mag=shift)
 times.append((time.perf_counter()-t)*1000)
 assert gui.current_sum is old_sum
 assert gui.delay.value()==old_delay
 assert gui.graph_mag.display_offset_db==old_offset
 assert gui.phase_match_label.text()==old_percent
 assert gui.sum_ref_label.text()==old_delta
print("MAG_GESTURE_NO_DSP_OR_RECALC_PASS",np.round(times,2).tolist(),"P95",np.percentile(times,95))
mag_after=(gui.graph_mag.y_min,gui.graph_mag.y_max)
phase_after=(gui.graph_phase.y_min,gui.graph_phase.y_max)
gui.align()
assert abs(gui.delay.value()-4.8)<.1
assert (gui.graph_mag.y_min,gui.graph_mag.y_max)==mag_after
assert (gui.graph_phase.y_min,gui.graph_phase.y_max)==phase_after
print("AUTO_ALIGN_PRESERVES_BOTH_NATIVE_Y_PASS")
gui.ref_choice.setCurrentIndex(1)
pre=(gui.graph_mag.y_min,gui.graph_mag.y_max)
gui.on_native_dual_pan((key,DualPanResult(
    PanFrame(23,.98,True,"stale",8,time.monotonic()),
    PanFrame(23,.98,True,"stale",8,time.monotonic()))))
assert (gui.graph_mag.y_min,gui.graph_mag.y_max)==pre
print("REF_SWITCH_INVALIDATES_STALE_DUAL_RESULT_PASS")
gui.close();app.processEvents()
print("V82_DUAL_AXIS_QT_QA_ALL_PASS",flush=True)
