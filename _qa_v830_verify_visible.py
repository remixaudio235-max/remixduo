import time,win32gui,win32api,win32con
from pathlib import Path
from PIL import ImageGrab
from plot_geometry_v7 import locate_plots
from plot_role_v812 import locate_role_plots
p=Path(__file__).resolve().parent
h=win32gui.FindWindow(None,'Smaart Suite')
print('SMAART',h,'ISICONIC',win32gui.IsIconic(h),flush=True)
if win32gui.IsIconic(h):win32gui.ShowWindow(h,win32con.SW_RESTORE)
for i in range(4):
 if win32gui.GetForegroundWindow()==h:break
 try:
  win32api.keybd_event(win32con.VK_MENU,0,0,0)
  time.sleep(.03)
  win32gui.SetForegroundWindow(h)
 except Exception as exc:print('FOCUS_RETRY',i,str(exc)[:60],flush=True)
 finally:win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
 time.sleep(.15)
print('FRONT',win32gui.GetForegroundWindow(),'GEOM',locate_plots(h),'ROLES',locate_role_plots(h),flush=True)
if win32gui.GetForegroundWindow()!=h:raise SystemExit('FOCUS_BLOCKED')
time.sleep(4)
front=win32gui.GetForegroundWindow()
print('AFTER_4S_FRONT',front,flush=True)
if front==h:
 path=p/'_qa_v830_sum_overlay_live.png'
 ImageGrab.grab(all_screens=True).save(path)
 print('CAPTURE',str(path),flush=True)
else:print('FOCUS_LOST_NO_CAPTURE',flush=True)
