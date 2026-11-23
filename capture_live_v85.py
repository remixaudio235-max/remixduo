from pathlib import Path
import time,win32gui,win32con
from PIL import ImageGrab
root=Path(__file__).resolve().parent
h=win32gui.FindWindow(None,"Smaart Suite")
lines=[f"Smaart hwnd={h} initially_iconic={win32gui.IsIconic(h)}"]
try:
    win32gui.ShowWindow(h,win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(h)
    lines.append("Requested native Smaart foreground")
except Exception as exc:
    lines.append("FOREGROUND_ERROR "+str(exc))
time.sleep(1)
front=win32gui.GetForegroundWindow()
lines.append("Front="+win32gui.GetWindowText(front))
lines.append("Smaart is foreground="+str(front==h))
ImageGrab.grab(all_screens=False).save(root/"V85_REMIX_SIGNAL_LIVE.png")
(root/"V85_NATIVE_FOCUS_QA.log").write_text("\n".join(lines),encoding="utf8")
