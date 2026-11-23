"""Read-only Win32 hit-test of actual LF/HF grips over Smaart Mag + Phase."""
from pathlib import Path
import time,win32gui,win32api,win32con,win32process,psutil
from plot_role_v812 import locate_role_plots
from roi_markers_v73 import hz_to_x

p=Path(__file__).resolve().parent
hwnd=win32gui.FindWindow(None,"Smaart Suite")
if not hwnd or win32gui.IsIconic(hwnd):
    raise SystemExit("HOLD_SMAART_NOT_VISIBLE")
owners=set()
for proc in psutil.process_iter(['pid','name','cmdline']):
    try:
        if proc.info['name'].lower()!='pythonw.exe':continue
        if any('windows_v8_27_MAG_NATIVE_SYNC_QA' in arg for arg in proc.info['cmdline']):
            owners.add(proc.info['pid'])
    except (psutil.Error,TypeError):
        pass
if not owners:raise SystemExit('HOLD_NO_REMIX_OWNER')
for i in range(5):
    if win32gui.GetForegroundWindow()==hwnd:break
    try:
        win32api.keybd_event(win32con.VK_MENU,0,0,0)
        time.sleep(.03)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:pass
    finally: win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
    time.sleep(.15)
if win32gui.GetForegroundWindow()!=hwnd:
    raise SystemExit('HOLD_FOCUS_NOT_SMAART')
time.sleep(2.2)
plots=locate_role_plots(hwnd)
if plots is None:
    raise SystemExit('HOLD_NO_NATIVE_PLOTS')
print('OWNERS',owners,'PLOTS',plots,flush=True)
for plotname,rect in (('phase',plots.phase),('mag',plots.mag)):
    l,t,w,h=rect
    for kind,hz in (('LF',60.),('HF',200.)):
        x=round(hz_to_x(hz,l,w))
        y=t+min(h-12,max(55,h//2))
        target=win32gui.WindowFromPoint((x,y))
        pid=win32process.GetWindowThreadProcessId(target)[1] if target else None
        classname=win32gui.GetClassName(target) if target else None
        print('HIT',plotname,kind,'POINT',x,y,'HWND',target,
              'PID',pid,'CLASS',classname,
              'REMIX_OWNER',pid in owners,flush=True)
        if pid not in owners:
            raise SystemExit('HOLD_MISSING_'+plotname+'_'+kind)
print('V832_MAG_PHASE_LF_HF_WIN32_HIT_PASS',flush=True)
