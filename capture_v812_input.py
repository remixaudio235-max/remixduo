from pathlib import Path
import time,win32gui,win32con,win32com.client
from PIL import ImageGrab
root=Path(__file__).resolve().parent
h=win32gui.FindWindow(None,"Smaart Suite")
lines=[f"HWND {h}"]
try:
    shell=win32com.client.Dispatch("WScript.Shell")
    shell.AppActivate("Smaart Suite")
    time.sleep(.35)
except Exception as exc:lines.append(str(exc))
time.sleep(.5)
lines.append(f"FG {win32gui.GetWindowText(win32gui.GetForegroundWindow())}")
img=ImageGrab.grab(all_screens=False)
img.save(root/"V812_BASE_SMAART_SCREEN.png")
(root/"V812_CAPTURE_LOG.txt").write_text("\n".join(lines),encoding="utf8")
