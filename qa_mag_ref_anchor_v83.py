from pathlib import Path
from PIL import Image
import numpy as np,win32gui,time
from trf_core import read_trf,matched,compute_sum
from mag_ref_anchor_v83 import fit_magnitude_ref,capture_mag_ref
from plot_geometry_v7 import locate_plots
root=Path(__file__).resolve().parent
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(p/"4,8 ms delay-1.trf")
b=read_trf(p/"0 delay-1.trf")
h=win32gui.FindWindow(None,"Smaart Suite")
r=locate_plots(h).mag
print("SMAART_MAG_RECT",r)
# The native screenshot was captured with the same pair selected.
im=Image.open(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_9_NATIVE_AXIS_CAL_QA\V79_LIVE_SMAART_GUI.png")
for lo,hi in [(-80,-44),(-67.79,-31.79),(-21,15)]:
    t=time.perf_counter()
    anchor=fit_magnitude_ref(im,r,(0,0,im.width,im.height),a,b,lo,hi)
    print("FIT_NATIVE_SCREEN",lo,hi,anchor,"MS",round((time.perf_counter()-t)*1000,1),flush=True)
# Blank screenshot must reject - no fabricated baseline.
blank=Image.new("RGB",im.size,(0,0,0))
negative=fit_magnitude_ref(blank,r,(0,0,im.width,im.height),a,b,-67.79,-31.79)
assert not negative.accepted,negative
print("FAIL_CLOSED_EMPTY_PASS")
