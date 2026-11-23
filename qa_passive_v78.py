from pathlib import Path
import numpy as np,time
import win32gui
from PyQt6.QtWidgets import QApplication
from passive_phase_y_v78 import infer_native_pan,NativeAxisFollower
from phase_axis_follow_v77 import capture_native_phase
from trf_core import read_trf
from overlay_v7 import App

hwnd=win32gui.FindWindow(None,"Smaart Suite")
assert hwnd and not win32gui.IsIconic(hwnd)
rect=(252,112,1442,398)
src=capture_native_phase(hwnd,rect)
print("NATIVE_PHASE_MASK",src.shape,int(src.sum()),flush=True)
def moved(mask,dy):
    out=np.zeros_like(mask)
    if dy>0:out[dy:]=mask[:-dy]
    elif dy<0:out[:dy]=mask[-dy:]
    else:out[:]=mask
    return out
for shift in (-73,-31,-8,0,9,31,74):
    t0=time.perf_counter()
    result=infer_native_pan(src,moved(src,shift))
    elapsed=(time.perf_counter()-t0)*1000
    assert result.valid and abs(result.shift_px-shift)<=1,(shift,result)
    print("NATIVE_PASSIVE_SHIFT_PASS",shift,result.shift_px,round(result.confidence,3),
          "detect_ms",round(elapsed,1),flush=True)
none=np.zeros_like(src)
assert not infer_native_pan(src,none).valid
print("NATIVE_FAIL_CLOSED_NO_TRACE_PASS")

app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
root=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(root/n) for n in ("4,8 ms delay-1.trf","0 delay-1.trf"))
gui.current_traces=(a,b)
gui.current_pair=(str(a.path),str(b.path))
gui.recalc()
gui.delay.setValue(4.8)
gui.plot_hwnd=hwnd
gui.plot_layout=type("PlotRects",(),{"phase":rect,"mag":(252,553,1442,398)})()
gui._apply_plot_layout()
key=(hwnd,rect,tuple(gui.current_pair))
raw_sum=gui.current_sum
old_lo=gui.graph_phase.y_min
old_hi=gui.graph_phase.y_max
delay=gui.delay.value()
match=gui.phase_match_label.text()
delta=gui.sum_ref_label.text()
from phase_axis_follow_v77 import PanObservation
gui.on_passive_axis_snapshot((key,PanObservation(31,.88,True,"native shift")))
assert gui.graph_phase.y_min>old_lo
assert gui.graph_phase.y_max>old_hi
assert gui.current_sum is raw_sum
assert gui.delay.value()==delay
assert gui.phase_match_label.text()==match
assert gui.sum_ref_label.text()==delta
print("GUI_FOLLOW_WITHOUT_RECOMPUTE_PASS",
      old_lo,gui.graph_phase.y_min,gui.phase_axis_note.text(),flush=True)
gui.on_passive_axis_snapshot((key,PanObservation(0,.10,False,"Unrelated trace redraw")))
assert gui.current_sum is raw_sum
gui.align()
assert gui.last_solve and abs(gui.last_solve[0].delay_ms-4.8)<.1
assert gui.graph_phase.y_min>old_lo
print("AUTO_ALIGN_RETAINS_SMAART_Y_PASS",gui.graph_phase.y_min,flush=True)
gui.close()
app.processEvents()
print("V78_PASSIVE_QA_ALL_PASS",flush=True)
