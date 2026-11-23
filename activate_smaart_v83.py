from pathlib import Path
import time,win32gui,win32con
root=Path(__file__).resolve().parent
h=win32gui.FindWindow(None,"Smaart Suite")
log=[]
log.append(f"window={h} iconic_before={win32gui.IsIconic(h)}")
win32gui.ShowWindow(h,win32con.SW_RESTORE)
try:
    win32gui.SetForegroundWindow(h)
    log.append("SetForegroundWindow requested")
except Exception as exc:
    log.append("FOREGROUND_DENIED "+str(exc))
time.sleep(.6)
log.append(f"foreground_is_smaart={win32gui.GetForegroundWindow()==h}")
(root/"V83_FOCUS_PROBE.log").write_text("\n".join(log),encoding="utf8")
