import time,concurrent.futures,win32gui,win32con,win32process
from pathlib import Path
from live_sync_v7 import LiveDataBarV7
from win_databar_v7 import locate_smaart
def restore(hwnd,unused):
    if win32gui.GetWindowText(hwnd)=="Smaart Suite":
        win32gui.ShowWindow(hwnd,win32con.SW_RESTORE)
win32gui.EnumWindows(restore,None)
w=locate_smaart()
print("WINDOW",w,flush=True)
if w:
    observer=LiveDataBarV7(Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data")
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        for i in range(4):
            begin=time.perf_counter()
            result=pool.submit(observer.poll,w.hwnd).result(timeout=20)
            print("POLL",i,result,"ELAPSED",round(time.perf_counter()-begin,3),
                  "COVERAGE",len(observer.states),"SCAN",observer.scan_count,flush=True)
            time.sleep(.15)
