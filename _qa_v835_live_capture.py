"""Capture actual Smaart overlay with crossover highlight; no audio actions."""
from pathlib import Path
import time,win32gui,win32api,win32con
from PIL import ImageGrab
from plot_role_v812 import locate_role_plots
root=Path(__file__).resolve().parent
h=win32gui.FindWindow(None,"Smaart Suite")
if not h:raise SystemExit("SMAART_NOT_FOUND")
if win32gui.IsIconic(h):
    win32gui.ShowWindow(h,win32con.SW_RESTORE)
    time.sleep(.3)
for _ in range(5):
    if win32gui.GetForegroundWindow()==h:break
    try:
        win32api.keybd_event(win32con.VK_MENU,0,0,0)
        win32gui.SetForegroundWindow(h)
    except Exception:pass
    finally:win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
    time.sleep(.16)
if win32gui.GetForegroundWindow()!=h:raise SystemExit("FOREGROUND_HOLD")
role=locate_role_plots(h)
if role is None:raise SystemExit("PLOTS_NOT_VALID")
time.sleep(2.)
path=root/'V835_CROSSOVER_LIVE_QA.png'
ImageGrab.grab(all_screens=True).save(path)
print("V835_CAPTURED",path,role,flush=True)
