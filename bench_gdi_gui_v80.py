import time,traceback,win32gui,win32con,numpy as np
from pathlib import Path
from fast_native_capture_bench import DesktopRoiCapture
from phase_axis_absolute_v79 import fit_ref_phase_axis
from plot_geometry_v7 import locate_plots
from trf_core import read_trf
p=Path(__file__).resolve().parent
log=p/'V80_GDI_BENCH_REAL.log'
h=win32gui.FindWindow(None,"Smaart Suite")
try:
 win32gui.ShowWindow(h,win32con.SW_RESTORE)
 win32gui.SetForegroundWindow(h)
except Exception as exc:pass
time.sleep(.35)
front=win32gui.GetForegroundWindow()
with open(log,'w',encoding='utf-8') as f:f.write(f'FRONT {win32gui.GetWindowText(front)} h={h}\n')
x,y,w,hh=locate_plots(h).phase
a=read_trf(Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data/4,8 ms delay-1.trf")
b=read_trf(Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data/0 delay-1.trf")
dc=DesktopRoiCapture()
ct=[];ft=[]
for i in range(24):
 t=time.perf_counter();image=dc.capture(x,y,w,hh);ct.append((time.perf_counter()-t)*1000)
 t=time.perf_counter();fit=fit_ref_phase_axis(image,(0,0,w,hh),(0,0,w,hh),a,b,180);ft.append((time.perf_counter()-t)*1000)
 if i==0:image.save(p/"V80_GDI_CAPTURE_REAL.png")
with open(log,'a',encoding='utf-8') as f:
 f.write("CAPTURE_MS_MEAN %.2f P95 %.2f\n"%(np.mean(ct),np.percentile(ct,95)))
 f.write("FIT_MS_MEAN %.2f P95 %.2f\n"%(np.mean(ft),np.percentile(ft,95)))
 f.write("FIT %s\n"%str(fit))
 f.write("RAW_TIMES %s\n"%np.round(ct,1).tolist())
dc.close()
