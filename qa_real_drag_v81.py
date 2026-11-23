"""One read-only test of current Smaart Phase Y drag. Restore same gesture."""
from pathlib import Path
import time,traceback,win32gui,win32api,win32con
from plot_geometry_v7 import locate_plots
from phase_axis_follow_v77 import capture_native_phase
from passive_phase_y_v78 import infer_native_pan
p=Path(__file__).resolve().parent
log=p/"V81_NATIVE_DRAG_ACTUAL.log"
out=[]
def record(x):
 out.append(str(x))
 log.write_text("\n".join(out),encoding="utf8")
h=win32gui.FindWindow(None,"Smaart Suite")
if win32gui.GetForegroundWindow()!=h:
 record("HOLD: Smaart not in foreground, no input sent")
 raise SystemExit(0)
rect=locate_plots(h).phase
x=rect[0]-30;y=rect[1]+round(rect[3]*.5)
start=win32api.GetCursorPos()
before=capture_native_phase(h,rect)
down=False
changed=False
def drag(first,second):
 global down
 win32api.SetCursorPos((x,first));time.sleep(.07)
 win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
 down=True;time.sleep(.09)
 for i in range(1,10):
  win32api.SetCursorPos((x,round(first+(second-first)*i/9)))
  time.sleep(.035)
 win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
 down=False;time.sleep(.3)
try:
 drag(y,y+38)
 changed=True
 after=capture_native_phase(h,rect)
 result=infer_native_pan(before,after)
 record("NATIVE_MOVE "+repr(result))
finally:
 if down:
  win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
 if changed:
  try:
   drag(y+38,y)
   back=capture_native_phase(h,rect)
   record("RESTORE "+repr(infer_native_pan(before,back)))
  except Exception as exc:
   record("RESTORE_ERROR "+repr(exc))
 win32api.SetCursorPos(start)
record("V81_REAL_DRAG_QA_COMPLETED")
