"""Safe real Smaart Phase Y-ruler drag QA, with an immediate reverse and unchanged audio."""
import time,sys,ctypes
from pathlib import Path
import win32gui,win32api,win32con
from PIL import ImageGrab
p=Path(__file__).resolve().parent
sys.path.insert(0,str(p))
from plot_role_v812 import locate_role_plots
from full_scan_v7 import printwindow_image
from native_fast_pan_v81 import colored_profiles,infer_pan
try:
 import win32com.client
except ImportError: win32com=None
hwnd=win32gui.FindWindow(None,'Smaart Suite')
if not hwnd: raise SystemExit('HOLD: SMAART NOT FOUND')
print("SMAART",hwnd,flush=True)
if win32com:
 print('APP_ACTIVATE',bool(win32com.client.Dispatch('WScript.Shell').AppActivate('Smaart Suite')),flush=True)
time.sleep(.12)
for focus_attempt in range(4):
 if win32gui.GetForegroundWindow()==hwnd:break
 try:
  win32api.keybd_event(win32con.VK_MENU,0,0,0)
  time.sleep(.035)
  win32gui.ShowWindow(hwnd,win32con.SW_RESTORE)
  win32gui.SetForegroundWindow(hwnd)
 except Exception as exc:
  print('FOCUS_ATTEMPT',focus_attempt,repr(exc),flush=True)
 finally:
  win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
 time.sleep(.11)
front=win32gui.GetForegroundWindow()
print('FOREGROUND',front,'EXPECTED',hwnd,flush=True)
if front!=hwnd: raise SystemExit('HOLD: SMAART NOT FOREGROUND, no drag')
phase=locate_role_plots(hwnd).phase
x,y,w,h=phase
print('PHASE_RECT',phase,flush=True)
if not (x>=180 and 300<=w<=1900 and 240<=h<=650):
 raise SystemExit('HOLD: invalid phase geometry')
winrect=win32gui.GetWindowRect(hwnd)
left,top,_,_=winrect
off=max(65,int(w*.105))
def native():
 im=printwindow_image(hwnd)
 region=im.crop((x+off-left,y-top,x+off-left+440,y+h-top))
 return colored_profiles(region)
def snap(name):
 ImageGrab.grab(all_screens=True).save(str(p/name))
 print("SAVED",name,flush=True)
origin=win32api.GetCursorPos()
cx,cy=x-22,y+h//2
delta=36
held=False
try:
 before,pixels=native()
 snap('_qa_phase_gui_before.png')
 print('PIXELS_BEFORE',pixels,flush=True)
 win32api.SetCursorPos((cx,cy));time.sleep(.18)
 if win32gui.GetForegroundWindow()!=hwnd:
  raise RuntimeError('Smaart lost focus before click')
 win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0,0,0)
 held=True
 for step in range(1,13):
  win32api.SetCursorPos((cx,cy+round(delta*step/12)));time.sleep(.045)
 time.sleep(.45)
 after,pixels2=native()
 result=infer_pan(before,after)
 print('NATIVE_AFTER_DRAG',pixels2,result,flush=True)
 snap('_qa_phase_gui_drag_down.png')
 for step in range(1,13):
  win32api.SetCursorPos((cx,cy+delta-round(delta*step/12)));time.sleep(.045)
 time.sleep(.2)
 recovered,px3=native()
 print('NATIVE_RESTORED',px3,infer_pan(before,recovered),flush=True)
 snap('_qa_phase_gui_restored.png')
finally:
 if held:win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)
 win32api.SetCursorPos(origin)
 print('SAFE_RELEASE',flush=True)
