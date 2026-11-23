from pathlib import Path
from PIL import Image
import numpy as np,time,win32gui
from PyQt6.QtWidgets import QApplication
from trf_core import read_trf,compute_sum
from plot_geometry_v7 import locate_plots
from full_scan_v7 import printwindow_image
from phase_axis_absolute_v79 import capture_fit,fit_ref_phase_axis
from overlay_v7 import App

h=win32gui.FindWindow(None,"Smaart Suite")
geo=locate_plots(h)
assert geo and geo.phase[2]>1000
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
ref=read_trf(p/"4,8 ms delay-1.trf")
other=read_trf(p/"TUNNINNGGG-8.trf")
t0=time.perf_counter()
for r,o in ((ref,other),(other,ref)):
    fit=capture_fit(h,geo.phase,r,o,center_top=204.3)
    assert fit.accepted and 100<=fit.top_deg<=130 and fit.hit_fraction>.88,fit
    print("NATIVE_REAL_REF_FIT",r.path.name,fit,"MS",
          round((time.perf_counter()-t0)*1000),flush=True)
original=printwindow_image(h)
x,y,w,hh=geo.phase
wl,wt,wr,wb=win32gui.GetWindowRect(h)
image=np.array(original.convert("RGB"))
roi=image[y-wt:y-wt+hh,x-wl:x-wl+w].copy()
for dy in (-60,-24,31,70):
    changed=image.copy()
    out=np.zeros_like(roi)
    if dy>0:out[dy:]=roi[:-dy]
    else:out[:dy]=roi[-dy:]
    changed[y-wt:y-wt+hh,x-wl:x-wl+w]=out
    fitted=fit_ref_phase_axis(Image.fromarray(changed),geo.phase,(wl,wt,wr,wb),
                               ref,other,center_top=117)
    expected=117+dy*360/hh
    assert fitted.accepted and abs(fitted.top_deg-expected)<8,(dy,fitted,expected)
    print("ABSOLUTE_SHIFT_FIT_PASS",dy,round(fitted.top_deg,1),
          "target",round(expected,1),flush=True)
# Offscreen GUI callback: absolute axis fit must not alter physical TF calculation.
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
gui.current_pair=(str(ref.path),str(other.path))
gui.current_traces=(ref,other)
gui.recalc()
gui.plot_hwnd=h
gui.plot_layout=geo
gui._apply_plot_layout()
gui.delay.setValue(-1.1)
gui.invert.setChecked(True)
old_sum=gui.current_sum
old_match=gui.phase_match_label.text()
old_delta=gui.sum_ref_label.text()
old_delay=gui.delay.value()
old_inv=gui.invert.isChecked()
old_top=gui.graph_phase.y_max
key=(h,geo.phase,tuple(gui.current_pair),0)
fit=capture_fit(h,geo.phase,ref,other,center_top=old_top)
gui.on_absolute_phase_axis((key,fit))
assert abs(gui.graph_phase.y_max-fit.top_deg)<1e-9
assert gui.current_sum is old_sum
assert gui.delay.value()==old_delay and gui.invert.isChecked()==old_inv
assert gui.phase_match_label.text()==old_match and gui.sum_ref_label.text()==old_delta
print("FIXED_ABSOLUTE_NATIVE_Y_PASS",
      old_top,gui.graph_phase.y_max,gui.phase_axis_note.text(),flush=True)
gui.align()
assert abs(gui.graph_phase.y_max-fit.top_deg)<1e-9
print("AUTO_ALIGN_NO_Y_REVERT_PASS",gui.graph_phase.y_max,flush=True)
# REF changed: asynchronous poll key must protect against stale calibration.
gui.ref_choice.setCurrentIndex(1)
after_ref=gui.graph_phase.y_max
gui.on_absolute_phase_axis((key,fit))
assert gui.graph_phase.y_max==after_ref
key2=(h,geo.phase,tuple(gui.current_pair),1)
fit2=capture_fit(h,geo.phase,other,ref,center_top=after_ref)
gui.on_absolute_phase_axis((key2,fit2))
assert abs(gui.graph_phase.y_max-fit2.top_deg)<1e-9
print("REF_CHANGED_ABSOLUTE_AXIS_PASS",fit2.top_deg)
gui.close();app.processEvents()
print("V79_NATIVE_ABSOLUTE_AXIS_ALL_QA_PASS",flush=True)
