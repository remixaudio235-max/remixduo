from pathlib import Path
import subprocess,time,win32gui,win32process,win32com.client,win32con,psutil
v7=17828
def visible():
    out=[]
    def cb(hwnd,unused):
        if not win32gui.IsWindow(hwnd):return
        _,pid=win32process.GetWindowThreadProcessId(hwnd)
        if pid==v7:
            out.append((hex(hwnd),win32gui.GetWindowText(hwnd),
                bool(win32gui.IsWindowVisible(hwnd)),win32gui.GetWindowRect(hwnd)))
    win32gui.EnumWindows(cb,None)
    return out
print("BEFORE",visible(),flush=True)
p=subprocess.Popen(["notepad.exe"])
time.sleep(.6)
shell=win32com.client.Dispatch("WScript.Shell")
shell.AppActivate(p.pid)
time.sleep(.35)
fg=win32gui.GetForegroundWindow()
print("FOREGROUND",win32gui.GetWindowText(fg),flush=True)
print("AFTER_UNRELATED_FOCUS",visible(),flush=True)
windows=visible()
# Panel and both chart overlays must hide when a foreign process is foreground.
if "Notepad" in win32gui.GetWindowText(fg) or "Untitled" in win32gui.GetWindowText(fg):
    assert not any(is_shown for hwnd,title,is_shown,rect in windows)
    print("V7_UNRELATED_WINDOW_HIDE_PASS",flush=True)
else:
    print("V7_UNRELATED_WINDOW_HIDE_HOLD: unable to activate Notepad",flush=True)
p.terminate()
time.sleep(.2)
shell.AppActivate("Smaart Suite")
