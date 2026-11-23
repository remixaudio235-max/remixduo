from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import QApplication
from plot_geometry_v7 import locate_plots,Plots
from trf_core import read_trf
from overlay_v7 import App
import win32gui,time

root=Path(__file__).resolve().parent
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
gui.show()
app.processEvents()
print("PANEL",gui.size().width(),gui.size().height(),flush=True)
assert gui.width()==205 and gui.height()==330
assert not gui.tabs.isVisible()
assert not gui.mag.isVisible() and not gui.phase.isVisible() and not gui.mag_fit.isVisible()
assert not gui.mag_min.isVisible() and not gui.phase_min.isVisible()
assert gui.mag.isChecked() and gui.phase.isChecked() and gui.mag_fit.isChecked()
h=win32gui.FindWindow(None,"Smaart Suite")
base=locate_plots(h)
assert base is not None
top,bottom=base.phase,base.mag
# User currently has Magnitude on TOP and Phase on BOTTOM.
layout=Plots(bottom,top,time.perf_counter())
gui.on_plot_layout((h,layout))
assert gui.plot_layout.mag==top and gui.plot_layout.phase==bottom
assert gui.graph_mag.geometry().getRect()==top
assert gui.graph_phase.geometry().getRect()==bottom
gui._position_roi_markers()
for marker in gui.roi_markers.values():
    assert bottom[1]<=marker.y()<=bottom[1]+bottom[3]
print("MAG_UPPER_PHASE_LOWER_AND_ROI_ANCHOR_PASS",flush=True)
base2=Plots(top,bottom,time.perf_counter())
gui.on_plot_layout((h,base2))
assert gui.graph_phase.geometry().getRect()==top
assert gui.graph_mag.geometry().getRect()==bottom
for marker in gui.roi_markers.values():
    assert top[1]<=marker.y()<=top[1]+top[3]
print("PHASE_UPPER_MAG_LOWER_AND_ROI_ANCHOR_PASS",flush=True)
gui.on_plot_layout(None)
assert not gui.overlay_positioned and gui.plot_layout is None
print("UNKNOWN_LAYOUT_FAIL_CLOSED_PASS")
paths=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(paths/n) for n in ("SUb.trf","FULL.trf"))
gui.current_pair=(str(a.path),str(b.path))
gui.current_traces=(a,b)
gui._update_delay_route_label()
gui.recalc()
gui.align()
assert abs(gui.delay.value()-13.2)<.2
assert gui.current_sum is not None
assert all(c.isChecked() for c in (gui.mag,gui.phase,gui.mag_fit))
app.processEvents()
assert gui.grab().save(str(root/"V812_MINI_PANEL_QA.png"))
print("AUTO_ALIGN_AND_ALWAYS_ON_PASS",gui.delay.value(),flush=True)
gui.close()
app.processEvents()
print("V812_MINIMAL_DYNAMIC_PLOTS_ALL_PASS",flush=True)
