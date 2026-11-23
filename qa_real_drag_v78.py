from pathlib import Path
import time, traceback
import win32gui,win32api,win32con
from phase_axis_follow_v77 import capture_native_phase
from passive_phase_y_v78 import infer_native_pan
ROOT=Path(__file__).resolve().parent
LOG=ROOT/"V78_REAL_DRAG_PROBE.log"
records=[]
def put(s):
    records.append(str(s))
    LOG.write_text("\n".join(records),encoding="utf-8")
h=win32gui.FindWindow(None,"Smaart Suite")
try:
    assert h and not win32gui.IsIconic(h)
    # Make Smaart active via a non-control title strip click; unlike
    # SetForegroundWindow, this uses normal physical focus behavior.
    win32api.SetCursorPos((800,10))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
    time.sleep(.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
    time.sleep(.25)
    f=win32gui.GetForegroundWindow()
    put("FOREGROUND "+str(f)+" "+win32gui.GetWindowText(f))
    if f!=h:
        put("HOLD: Smaart could not become foreground");raise SystemExit(0)
    rect=(252,112,1442,398)
    before=capture_native_phase(h,rect)
    x,y=224,300
    def drag(ay,by):
        win32api.SetCursorPos((x,ay));time.sleep(.09)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
        time.sleep(.12)
        for step in range(1,11):
            win32api.SetCursorPos((x,round(ay+(by-ay)*step/10)))
            time.sleep(.028)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
        time.sleep(.35)
    try:
        drag(y,y+42)
        mid=capture_native_phase(h,rect)
        shift=infer_native_pan(before,mid)
        put("REAL_SMAART_PAN "+repr(shift))
    finally:
        # Always reverse the exact input gesture to restore Smaart's view.
        drag(y+42,y)
        after=capture_native_phase(h,rect)
        back=infer_native_pan(before,after)
        put("RESTORED_SMAART_VIEW "+repr(back))
except BaseException as exc:
    put("PROBE_ERROR "+str(exc)+"\n"+traceback.format_exc())
