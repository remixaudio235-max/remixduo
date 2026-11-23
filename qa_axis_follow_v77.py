from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import QApplication
from phase_axis_follow_v77 import detect_vertical_shift,shifted_y_range,native_blue_mask
from overlay_v7 import App
from trf_core import read_trf

# Synthetic independent blue curve shift up/down, no Smaart screen manipulation.
rng=np.random.default_rng(77)
h,w=340,440
before=np.zeros((h,w),dtype=bool)
for x in range(3,w-3):
    ys=[int(68+24*np.sin(x/26)),int(180+35*np.sin(x/32)),int(270+21*np.cos(x/23))]
    for y in ys:
        before[max(0,y-1):min(h,y+2),x]=True
for shift in (-90,-37,-9,0,11,53,108):
    after=np.zeros_like(before)
    if shift>0:
        after[shift:,:]=before[:-shift,:]
    elif shift<0:
        after[:shift,:]=before[-shift:,:]
    else:
        after[:]=before
    got=detect_vertical_shift(before,after,max_shift=150)
    assert got.valid and abs(got.shift_px-shift)<=1,(shift,got)
    print("TRACK_SHIFT_PASS",shift,got.shift_px,round(got.confidence,3))
bad=np.zeros_like(before)
assert not detect_vertical_shift(before,bad).valid
print("TRACK_NO_TRACE_FAIL_CLOSED_PASS")
ymin,ymax=shifted_y_range(-360,0,398,53)
assert abs((ymax-ymin)-360)<1e-6
assert abs((ymax*398/360)-53)<1e-6
print("TRACK_Y_RANGE_PAN_PASS",ymin,ymax)

app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
source=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(source/"4,8 ms delay-1.trf")
b=read_trf(source/"0 delay-1.trf")
gui.current_traces=(a,b)
gui.recalc()
gui.delay.setValue(4.8)
gui.hf.setValue(401.2)
gui.plot_layout=type("NativePlot",(),{"phase":(252,112,1442,398),"mag":(252,553,1442,398)})()
gui._apply_plot_layout()
base_sum=gui.current_sum
base_match=gui.phase_match_label.text()
base_delta=gui.sum_ref_label.text()
base_delay=gui.delay.value()
base_candidates=gui.last_solve
start={"hwnd":123,"start":(224,181),"lo":gui.graph_phase.y_min,
       "hi":gui.graph_phase.y_max,"before":before,"rect":gui.plot_layout.phase,
       "preview_shift":0.}
gui._apply_phase_pan(53,start,verified=True,confidence=.81)
assert gui.current_sum is base_sum
assert gui.phase_match_label.text()==base_match
assert gui.sum_ref_label.text()==base_delta
assert gui.delay.value()==base_delay
assert gui.last_solve is base_candidates
assert abs(gui.graph_phase.y_min-gui.phase_min.value())<1.
assert abs(gui.graph_phase.y_max-gui.phase_max.value())<1.
print("NO_COMPLEX_SUM_OR_DELAY_RECALC_PASS",
      gui.graph_phase.y_min,gui.graph_phase.y_max,
      gui.phase_axis_note.text())
view_before=(gui.graph_phase.y_min,gui.graph_phase.y_max)
gui.align()
assert gui.last_solve and abs(gui.last_solve[0].delay_ms-4.8)<.11
assert (gui.graph_phase.y_min,gui.graph_phase.y_max)==view_before
print("AUTO_ALIGN_RETAINS_VIEWPORT_PASS",gui.graph_phase.y_min,gui.graph_phase.y_max)
gui.close()
app.processEvents()
print("V77_AXIS_FOLLOW_QA_PASS")
