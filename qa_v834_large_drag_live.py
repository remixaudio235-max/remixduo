"""Safe Smaart real Y-axis stress: 180px down/up, no audio changes.

Each test requires exact visible, foreground HWND. Press held while moving
down and back, then released at the original point. Dumps before/peak/return
desktop captures and logs. Never clicks a chart interior or playback controls.
"""
from pathlib import Path
import time,win32gui,win32api,win32con,sys
from PIL import ImageGrab
from plot_role_v812 import locate_role_plots

ROOT=Path(__file__).resolve().parent
HWND=win32gui.FindWindow(None,'Smaart Suite')
if not HWND:raise SystemExit('BLOCKED_SMAART_NOT_FOUND')
def focus():
 if win32gui.IsIconic(HWND):
  win32gui.ShowWindow(HWND,win32con.SW_RESTORE)
  time.sleep(.25)
 for _ in range(5):
  if win32gui.GetForegroundWindow()==HWND:return True
  try:
   win32api.keybd_event(win32con.VK_MENU,0,0,0)
   time.sleep(.05)
   win32gui.SetForegroundWindow(HWND)
  except Exception:pass
  finally:
   win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
  time.sleep(.14)
 return win32gui.GetForegroundWindow()==HWND
if not focus():raise SystemExit('BLOCKED_NOT_FOREGROUND')
role=locate_role_plots(HWND)
if role is None:raise SystemExit('BLOCKED_PLOT_ROLES_UNKNOWN')
print('V834_GEOMETRY',role,flush=True)
start_cursor=win32api.GetCursorPos()
def screenshot(name):
 try:
  ImageGrab.grab(all_screens=True).save(str(ROOT/('V834_'+name+'.png')))
  print('SHOT',name,round(time.perf_counter(),3),flush=True)
 except Exception as e:print('SHOT_ERROR',name,repr(e),flush=True)
def test(kind,rect):
 x,y,w,h=rect
 px,py=x-46,y+h//2
 span=160 if h>=350 else 120
 if not(x>180 and w>800 and h>300):
  raise RuntimeError('Suspicious geometry: '+str(rect))
 if not focus():raise RuntimeError('Focus lost before '+kind)
 time.sleep(.2)
 screenshot(kind+'_PRE')
 win32api.SetCursorPos((px,py))
 held=False
 try:
  if win32gui.GetForegroundWindow()!=HWND:
   raise RuntimeError('Focus changed before press')
  win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0,0,0)
  held=True
  for step in range(1,17):
   win32api.SetCursorPos((px,py+round(span*step/16)))
   time.sleep(.052)
  screenshot(kind+'_PEAK')
  for step in range(1,17):
   win32api.SetCursorPos((px,py+span-round(span*step/16)))
   time.sleep(.052)
  screenshot(kind+'_RETURN')
 finally:
  if held:
   win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)
  time.sleep(.2)
  screenshot(kind+'_SETTLED')
  print('DONE',kind,'PEAK_PX',span,flush=True)
try:
 test('PHASE',role.phase)
 test('MAG',role.mag)
finally:
 win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)
 win32api.SetCursorPos(start_cursor)
 print('RESTORED_MOUSE',flush=True)
