import time,win32gui,win32con,numpy as np
from pathlib import Path
from plot_geometry_v7 import locate_plots
from native_fast_pan_v81 import NativeFastPan
log=Path(__file__).with_name("V81_NATIVE_FAST_BENCH.log")
h=win32gui.FindWindow(None,"Smaart Suite")
try:
    win32gui.ShowWindow(h,win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(h)
except Exception:
    pass
time.sleep(.3)
front=win32gui.GetForegroundWindow()
rect=locate_plots(h).phase
tracker=NativeFastPan()
times=[];valid=0;bad=0;movement=[]
for i in range(22):
    frame=tracker.poll(("bench",rect),rect)
    times.append(frame.capture_ms)
    valid+=int(frame.valid)
    bad+=int(not frame.valid)
    if frame.valid and frame.delta_px:
        movement.append((frame.delta_px,round(frame.confidence,2)))
    time.sleep(.01)
log.write_text(
    f"FRONT={win32gui.GetWindowText(front)!r}\n"
    f"SMAART_HWND={h} PLOT={rect}\n"
    f"P50={np.percentile(times,50):.1f}ms P95={np.percentile(times,95):.1f}ms "
    f"MEAN={np.mean(times):.1f}ms\n"
    f"VALID={valid} BAD={bad} MOVEMENTS={movement}\n"
    f"SAMPLES={np.round(times,1).tolist()}\n",encoding="utf8")
