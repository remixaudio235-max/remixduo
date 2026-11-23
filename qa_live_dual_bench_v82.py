from pathlib import Path
import time,numpy as np,win32gui,win32con
from plot_geometry_v7 import locate_plots
from native_dual_y_v82 import NativeDualFastPan
p=Path(__file__).resolve().parent
log=p/"V82_REAL_DUAL_AXIS_BENCH.log"
h=win32gui.FindWindow(None,"Smaart Suite")
try:
    win32gui.ShowWindow(h,win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(h)
except Exception:pass
time.sleep(.4)
front=win32gui.GetWindowText(win32gui.GetForegroundWindow())
g=locate_plots(h)
watcher=NativeDualFastPan()
total=[];phase=[];mag=[];good=0
for i in range(22):
    t=time.perf_counter()
    r=watcher.poll(("v82qa",g.phase,g.mag),g.phase,g.mag)
    total.append((time.perf_counter()-t)*1000)
    phase.append(r.phase.capture_ms)
    mag.append(r.mag.capture_ms)
    good+=int(r.phase.valid and r.mag.valid)
    time.sleep(.02)
log.write_text(
    f"FOREGROUND={front!r} SMAART={h}\n"
    f"BOTH_VALID={good}/{len(total)}\n"
    f"TOTAL_DUAL_P50={np.percentile(total,50):.1f}ms P95={np.percentile(total,95):.1f}ms\n"
    f"PHASE_P50={np.percentile(phase,50):.1f}ms P95={np.percentile(phase,95):.1f}ms\n"
    f"MAG_P50={np.percentile(mag,50):.1f}ms P95={np.percentile(mag,95):.1f}ms\n"
    f"FRAME_TIMES={np.round(total,1).tolist()}\n",encoding="utf-8")
