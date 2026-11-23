"""Live signed Phase Y gesture with independent before/after raster evidence."""
from pathlib import Path
import time,sys,win32gui,win32api,win32con,numpy as np
from PIL import ImageGrab
p=Path(__file__).resolve().parent
sys.path.insert(0,str(p))
from plot_role_v812 import locate_role_plots
from full_scan_v7 import printwindow_image
from native_fast_pan_v81 import colored_profiles,infer_pan
from trf_core import read_trf
from phase_axis_absolute_v79 import fit_ref_phase_axis
hwnd=win32gui.FindWindow(None,'Smaart Suite')
if not hwnd:raise SystemExit('HOLD NO SMAART')
if win32gui.IsIconic(hwnd):
 win32gui.ShowWindow(hwnd,win32con.SW_RESTORE)
 time.sleep(.3)
 print('RESTORED_MINIMIZED_SMAART',flush=True)
def focus():
 for i in range(5):
  if win32gui.GetForegroundWindow()==hwnd:return True
  try:
   win32api.keybd_event(win32con.VK_MENU,0,0,0)
   time.sleep(.035)
   win32gui.SetForegroundWindow(hwnd)
  except Exception:pass
  finally:win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
  time.sleep(.12)
 return win32gui.GetForegroundWindow()==hwnd
if not focus():raise SystemExit('HOLD FOCUS')
plots=locate_role_plots(hwnd)
rect=plots.phase
x,y,w,h=rect
print('PHASE',rect,'SMAART',hwnd,flush=True)
src=Path.home()/'Documents/Smaart Suite/Data/Transfer Function/Session Data'
a=read_trf(src/'4,8 ms delay-1.trf')
b=read_trf(src/'rrt-3.trf')
left,top,*_=win32gui.GetWindowRect(hwnd)
off=max(65,int(w*.105))
def sample(tag):
 im=printwindow_image(hwnd)
 profiles,pixels=colored_profiles(im.crop((x+off-left,y-top,x+off-left+440,y+h-top)))
 scr=ImageGrab.grab()
 arr=np.asarray(scr.convert('RGB'),np.uint8)
 roi=arr[y+30:y+h-12,x+190:x+1000]
 green=((roi[:,:,1].astype(int)>170)&(roi[:,:,1].astype(int)>roi[:,:,0].astype(int)*1.7)&(roi[:,:,2]<140))
 count=int(green.sum())
 path=p/(tag+'.png');scr.save(path)
 fit=fit_ref_phase_axis(im,rect,(left,top,left+im.width,top+im.height),a,b,center_top=180.)
 print('FRAME',tag,'GREEN',count,'NATIVE_PIXELS',pixels,'FIT',fit,flush=True)
 return profiles,count,fit
# Wait until Smaart and the actual SUM overlay have both fully rendered.
base=None
for attempt in range(5):
 if not focus():raise SystemExit('FOCUS_LOST')
 profile,count,fit=sample('V829_PHASE_BEFORE' if attempt==4 else '_qa_phase_preflight')
 if count>800:
  base=(profile,count,fit);sample('V829_PHASE_BEFORE');break
 time.sleep(.45)
if base is None:raise SystemExit('HOLD NO VISIBLE SUM BEFORE GESTURE')
orig=win32api.GetCursorPos()
cx,cy=x-22,y+h//2
def gesture(dy,tag):
 if not focus():raise RuntimeError('Smaart not foreground')
 win32api.SetCursorPos((cx,cy))
 time.sleep(.13)
 if win32gui.GetForegroundWindow()!=hwnd:raise RuntimeError('Smaart focus changed')
 held=False
 try:
  win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0,0,0);held=True
  for step in range(1,15):
   win32api.SetCursorPos((cx,cy+round(dy*step/14)))
   time.sleep(.055)
  time.sleep(.24)
  during=sample(tag+'_HELD')
 finally:
  if held:win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)
 time.sleep(1.25)
 after=sample(tag+'_RELEASED')
 print('RESULT',tag,'RELATIVE',infer_pan(base[0],after[0]),flush=True)
 return during,after
try:
 down=gesture(+34,'V829_PHASE_DOWN')
 up=gesture(-34,'V829_PHASE_UP')
finally:
 win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0,0,0)
 win32api.SetCursorPos(orig)
 print('RESTORE_MOUSE',flush=True)
