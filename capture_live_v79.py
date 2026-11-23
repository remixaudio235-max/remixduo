from pathlib import Path
import time,win32gui,win32con
from PIL import ImageGrab
p=Path(__file__).resolve().parent
h=win32gui.FindWindow(None,'Smaart Suite')
win32gui.ShowWindow(h,win32con.SW_RESTORE)
try:
    win32gui.SetForegroundWindow(h)
except Exception as exc:
    (p/'V79_CAPTURE_FOCUS_ERROR.log').write_text(str(exc),encoding='utf8')
time.sleep(1.0)
ImageGrab.grab(all_screens=False).save(p/'V79_LIVE_SMAART_GUI.png')
f=win32gui.GetForegroundWindow()
(p/'V79_CAPTURE_FOREGROUND.txt').write_text(win32gui.GetWindowText(f),encoding='utf8')
