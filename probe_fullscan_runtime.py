from pathlib import Path
from win_databar_v7 import locate_smaart
from full_scan_v7 import full_scan
import win32gui,win32con,psutil,time
def restore(hwnd,unused):
    if win32gui.GetWindowText(hwnd)=="Smaart Suite":
        _,pid=__import__('win32process').GetWindowThreadProcessId(hwnd)
        if psutil.Process(pid).name().lower()=="smaart.exe":
            win32gui.ShowWindow(hwnd,win32con.SW_RESTORE)
win32gui.EnumWindows(restore,None)
time.sleep(.2)
f=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
m=locate_smaart()
print("V7_SMAART_WINDOW",m,flush=True)
if m:
    try:
        scan=full_scan(m.hwnd,f)
        print("V7_FULL_SCAN",scan,flush=True)
    except Exception as e:
        print("V7_FULL_SCAN_FAIL",type(e).__name__,str(e),flush=True)
