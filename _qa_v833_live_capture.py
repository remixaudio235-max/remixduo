from pathlib import Path
import time,win32gui,win32api,win32con
from PIL import ImageGrab
p=Path(__file__).resolve().parent
h=win32gui.FindWindow(None,'Smaart Suite')
if not h:raise SystemExit('SMAART_HOLD')
if win32gui.IsIconic(h):
 win32gui.ShowWindow(h,win32con.SW_RESTORE)
 time.sleep(.25)
 print('RESTORED_SMAART_FROM_MINIMIZE',flush=True)
for j in range(4):
 if win32gui.GetForegroundWindow()==h:break
 try:
  win32api.keybd_event(win32con.VK_MENU,0,0,0)
  win32gui.SetForegroundWindow(h)
 except Exception as ex: print('FOCUS_RETRY',type(ex).__name__)
 finally:win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
 time.sleep(.16)
print('FG',win32gui.GetForegroundWindow(),'SMAART',h,flush=True)
if win32gui.GetForegroundWindow()!=h:raise SystemExit('FOCUS_HOLD')
time.sleep(2)
path=p/'V833_COMPACT_TRACE_LIVE_QA.png'
ImageGrab.grab(all_screens=True).save(path)
print('CAPTURED',path,flush=True)
