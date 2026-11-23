from pathlib import Path
import time,numpy as np,win32gui
from PIL import Image
from PyQt6.QtWidgets import QApplication
from trf_core import read_trf,matched,compute_sum
from mag_ref_anchor_v83 import fit_magnitude_ref,MagAnchor
from native_fast_pan_v81 import PanFrame
from native_dual_y_v82 import DualPanResult
from overlay_v7 import App

p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(p/n) for n in ("4,8 ms delay-1.trf","0 delay-1.trf"))
img=Image.open(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_9_NATIVE_AXIS_CAL_QA\V79_LIVE_SMAART_GUI.png")
mag=(252,553,1442,398)
lo,hi=-67.79,-31.79
fit=fit_magnitude_ref(img,mag,(0,0,img.width,img.height),a,b,lo,hi)
assert fit.accepted and fit.score>=.82,(fit,)
assert abs(fit.offset_db+49.75)<.51,fit
print("NATIVE_REF_MAG_ANCHOR",fit,flush=True)
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
hwnd=win32gui.FindWindow(None,"Smaart Suite")
phase=(252,112,1442,398)
gui.current_pair=(str(a.path),str(b.path))
gui.current_traces=(a,b)
gui.recalc()
gui.delay.setValue(4.8)
gui.plot_hwnd=hwnd
gui.plot_layout=type("Plot",(),{"phase":phase,"mag":mag})()
gui._apply_plot_layout()
gui.graph_mag.y_min=lo
gui.graph_mag.y_max=hi
gui.mag_min.blockSignals(True)
gui.mag_max.blockSignals(True)
gui.mag_min.setValue(lo)
gui.mag_max.setValue(hi)
gui.mag_min.blockSignals(False)
gui.mag_max.blockSignals(False)
s=gui.current_sum
before_raw=s.mag_db.copy()
before_phase=s.phase_deg.copy()
old_value=-63.1
gui.graph_mag.display_offset_db=old_value
key=(hwnd,mag,tuple(gui.current_pair),0,
     float(gui.mag_smooth.currentData() or 0),round(lo,2),round(hi,2))
gui.on_mag_ref_anchor((key,fit))
new_value=gui.graph_mag.display_offset_db
assert new_value>old_value+12,(old_value,new_value)
assert abs(new_value+49.75)<.51
assert gui._mag_anchor_verified
assert gui.current_sum is s
assert np.array_equal(gui.current_sum.mag_db,before_raw)
assert np.array_equal(gui.current_sum.phase_deg,before_phase)
print("NATIVE_REF_VISUAL_OFFSET_CORRECTION_PASS",old_value,new_value,flush=True)
f,h1,h2,coh=matched(a,b)
for hz in (80,125,160,500,800,1000):
 idx=int(np.argmin(np.abs(f-hz)))
 rawref=20*np.log10(np.abs(h1[idx]))
 rawsum=20*np.log10(np.abs(h1[idx]+h2[idx]*np.exp(-2j*np.pi*f[idx]*.0048)))
 native_ref_y=(hi-(rawref+new_value))*mag[3]/(hi-lo)
 native_sum_y=(hi-(rawsum+new_value))*mag[3]/(hi-lo)
 difference=(native_ref_y-native_sum_y)*(hi-lo)/mag[3]
 assert difference>5.3 and difference<6.9,(hz,difference)
 print("PHYS_SUM_ABOVE_NATIVE_REF",round(f[idx],1),"Hz",
       "delta dB",round(difference,2),flush=True)
# Reject stale prior ref, or weak Mag pan without changing y.
current=gui.graph_mag.y_min
gui.on_native_mag_pan(((hwnd,mag,tuple(gui.current_pair),0),
                       PanFrame(34,.80,True,"noisy",20,time.monotonic())))
assert gui.graph_mag.y_min==current
print("SPURIOUS_MAG_PAN_CONF_080_REJECTED_PASS")
gui.on_native_mag_pan(((hwnd,mag,tuple(gui.current_pair),0),
                       PanFrame(2,.98,True,"actual",20,time.monotonic())))
assert gui.graph_mag.y_min>current
print("MAG_PAN_CONF_098_ACCEPTED_PASS")
# Anchor result from pre-pan frame must not overwrite post-pan transform.
past=gui.graph_mag.display_offset_db
gui.on_mag_ref_anchor((key,MagAnchor(-100,.95,.1,120,True,"stale")))
assert gui.graph_mag.display_offset_db==past
print("MAG_AXIS_STALE_FIT_REJECT_PASS")
gui.align()
assert abs(gui.delay.value()-4.8)<.1
assert gui.current_sum is not None
assert abs(gui.graph_mag.display_offset_db-new_value)<1e-8
print("AUTO_ALIGN_DOES_NOT_CHANGE_MAG_ANCHOR_PASS")
gui.ref_choice.setCurrentIndex(1)
assert not gui._mag_anchor_verified
print("REF_SWITCH_RESET_PASS")
gui.close()
app.processEvents()
print("V83_REAL_NATIVE_MAG_REF_QA_ALL_PASS",flush=True)
