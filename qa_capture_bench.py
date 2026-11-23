import time,statistics,win32gui
from PIL import ImageGrab
from full_scan_v7 import printwindow_image
from plot_geometry_v7 import locate_plots
from phase_axis_follow_v77 import capture_native_phase
from phase_axis_absolute_v79 import capture_fit,fit_ref_phase_axis
from pathlib import Path
from trf_core import read_trf
h=win32gui.FindWindow(None,"Smaart Suite")
rect=locate_plots(h).phase
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
ref=read_trf(p/"4,8 ms delay-1.trf")
other=read_trf(p/"0 delay-1.trf")
wl,wt,wr,wb=win32gui.GetWindowRect(h)
x,y,w,hh=rect
samples={}
funcs={
"full_PrintWindow":lambda:printwindow_image(h),
"PIL_ImageGrab_plot":lambda:ImageGrab.grab(bbox=(x,y,x+w,y+hh),all_screens=True),
"native_mask_capture":lambda:capture_native_phase(h,rect),
"absolute_fit_PrintWindow":lambda:capture_fit(h,rect,ref,other),
}
for name,func in funcs.items():
 t=[];success=[]
 for i in range(8):
  start=time.perf_counter()
  obj=func()
  t.append((time.perf_counter()-start)*1000)
  if name=="PIL_ImageGrab_plot":success.append(obj.getpixel((200,100)))
  if name=="absolute_fit_PrintWindow":success.append((obj.accepted,obj.hit_fraction))
 samples[name]=t
 print(name,"mean",round(statistics.mean(t),2),"median",round(statistics.median(t),2),"p95",round(sorted(t)[-2],2),"samples",[round(v,1) for v in t],"values",success[:2],flush=True)
