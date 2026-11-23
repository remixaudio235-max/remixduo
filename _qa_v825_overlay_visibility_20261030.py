"""Native Windows V8.25 overlay visibility check; only foregrounds Smaart."""
import win32gui,win32process,psutil,time
from PIL import ImageGrab
from pathlib import Path
h=win32gui.FindWindow(None,"Smaart Suite")
def asc(s):return str(s).encode("ascii","backslashreplace").decode("ascii")
before=win32gui.GetForegroundWindow()
print("BEFORE",before,asc(win32gui.GetWindowText(before)),flush=True)
if h and not win32gui.IsIconic(h):
    try:win32gui.SetForegroundWindow(h)
    except Exception as e: print("SET_FOREGROUND_ERROR",asc(repr(e)),flush=True)
time.sleep(3.8)
f=win32gui.GetForegroundWindow()
print("AFTER",f,asc(win32gui.GetWindowText(f)),flush=True)
wanted=set()
for p in psutil.process_iter(("pid","name","cmdline")):
    try:
        cmd=p.info.get("cmdline") or []
        if (any(str(v).lower().endswith("overlay_v7.py") for v in cmd) and
           "windows_v8_25_BUTTON_ONLY_COMPACT_QA" in p.cwd()):
            wanted.add(p.pid)
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
print("V825_PIDS",sorted(wanted),flush=True)
windows=[]
def cb(hwnd,arg):
    _,pid=win32process.GetWindowThreadProcessId(hwnd)
    if pid in wanted:
        windows.append((hwnd,pid,bool(win32gui.IsWindowVisible(hwnd)),
           asc(win32gui.GetWindowText(hwnd)),str(win32gui.GetWindowRect(hwnd)),win32gui.GetClassName(hwnd)))
win32gui.EnumWindows(cb,None)
for item in windows:print("QT_WINDOW",*item,flush=True)
out=Path(__file__).with_name("V825_AFTER_ROLE_REPAIR_SCREEN.png")
ImageGrab.grab(all_screens=False).save(out)
print("SCREEN_SAVED",out,flush=True)
