"""Read-only actual Smaart/RemiX toolbar screenshot after V8.31 code restart."""
from pathlib import Path
import time,win32gui,win32api,win32con
from PIL import ImageGrab
from pywinauto import Desktop
p=Path(__file__).resolve().parent
hwnd=win32gui.FindWindow(None,"Smaart Suite")
if not hwnd or win32gui.IsIconic(hwnd):
    raise SystemExit("NO_VISIBLE_SMAART")
for i in range(5):
    if win32gui.GetForegroundWindow()==hwnd:break
    try:
        win32api.keybd_event(win32con.VK_MENU,0,0,0)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:pass
    finally:win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
    time.sleep(.14)
print("SMAART_FOREGROUND",hwnd,win32gui.GetForegroundWindow(),flush=True)
if win32gui.GetForegroundWindow()!=hwnd:raise SystemExit("FOCUS_HOLD")
time.sleep(2.0)
im=ImageGrab.grab(all_screens=True)
target=p/"V831_BRAND_LIVE_QA.png"
im.save(target)
print("SCREENSHOT",target,im.size,flush=True)
