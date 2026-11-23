from pathlib import Path
import win32gui,win32con,time,numpy as np
from trf_core import read_trf
from plot_geometry_v7 import locate_plots
from fast_phase_y_v80 import capture_fit_fast
root=Path(__file__).resolve().parent
log=root/"V80_LIVE_FAST_CAPTURE_QA.log"
hwnd=win32gui.FindWindow(None,"Smaart Suite")
try:
 win32gui.ShowWindow(hwnd,win32con.SW_RESTORE)
 win32gui.SetForegroundWindow(hwnd)
except Exception as exc:
 log.write_text("FOCUS_EXCEPTION "+str(exc),encoding="utf-8")
time.sleep(.3)
foreground=win32gui.GetForegroundWindow()
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
ref=read_trf(p/"4,8 ms delay-1.trf")
other=read_trf(p/"0 delay-1.trf")
rect=locate_plots(hwnd).phase
events=[]
t0=time.perf_counter()
for i in range(30):
 r=capture_fit_fast(hwnd,rect,ref,other,center_top=180)
 events.append((r.mode, r.elapsed_ms,r.fit.accepted,r.fit.hit_fraction))
 time.sleep(.025)
ms=np.array([e[1] for e in events])
content=(f"HWND={hwnd} FRONT={win32gui.GetWindowText(foreground)!r}\n"
         f"N={len(events)} GDI_OK={sum(x[0]=='gdi' and x[2] for x in events)} "
         f"PRINT_OK={sum(x[0]=='printwindow' and x[2] for x in events)}\n"
         f"CAPTURE+FIT P50={np.percentile(ms,50):.1f}ms P95={np.percentile(ms,95):.1f}ms "
         f"MEAN={ms.mean():.1f}ms\n"
         f"SAMPLES={events[:7]}\n")
log.write_text(content,encoding="utf-8")
