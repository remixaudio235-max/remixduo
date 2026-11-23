"""Read-only live native registration plus deterministic fail-closed checks."""
from pathlib import Path
import win32gui
from PIL import Image
from trf_core import read_trf,compute_sum
from plot_geometry_v7 import locate_plots
from smaart_native_mag_fit import capture_native_window
from mag_sum_native_v826 import axis_from_native_image
root=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(root/"0 delay-2.trf")
b=read_trf(root/"4,8 ms delay-1.trf")
traces=(a,b)
# An empty frame must not produce an invented display offset.
empty=Image.new("RGB",(1920,1040),(0,0,0))
r=axis_from_native_image(empty,(252,553,1442,398),(0,0,1920,1040),traces)
assert not r.accepted,r
print("EMPTY_FAIL_CLOSED_PASS")
hwnd=win32gui.FindWindow(None,"Smaart Suite")
assert hwnd,"Smaart unavailable"
plot=locate_plots(hwnd)
assert plot and plot.mag[3]>240
im,rect=capture_native_window(hwnd)
axis=axis_from_native_image(im,plot.mag,rect,traces)
print("V826_NATIVE_AXIS",axis,flush=True)
assert axis.accepted,axis.reason
assert axis.color=="blue",axis
assert axis.source_index==1,axis
assert axis.score>=.82,axis
assert axis.y_max>axis.y_min,axis
# Swapping source order cannot alter recovered pixel Y transform.
swapped=axis_from_native_image(im,plot.mag,rect,(b,a))
assert swapped.accepted and swapped.source_index==0,swapped
assert abs(axis.y_max-swapped.y_max)<1e-5
assert abs(axis.y_min-swapped.y_min)<1e-5
s=compute_sum(a,b,delay_ms=4.8,invert_trace2=False)
assert len(s.hz)>100 and len(s.mag_db)==len(s.hz)
print("NATIVE_MAG_AXIS_READY_PASS","SOURCE_BLUE",round(axis.score,3),
      "Y_RANGE",round(axis.y_min,2),round(axis.y_max,2),flush=True)
