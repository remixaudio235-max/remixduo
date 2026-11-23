import time,win32gui,win32con,win32com.client,win32api
from PIL import ImageGrab
from pathlib import Path
root=Path(__file__).resolve().parent
h=win32gui.FindWindow(None,"Smaart Suite")
lines=[]
try:
    win32gui.ShowWindow(h,win32con.SW_RESTORE)
    shell=win32com.client.Dispatch("WScript.Shell")
    ok=shell.AppActivate("Smaart Suite")
    lines.append(f"WScript.AppActivate:{ok}")
    time.sleep(.35)
    if win32gui.GetForegroundWindow()!=h:
        win32api.keybd_event(win32con.VK_MENU,0,0,0)
        win32api.keybd_event(win32con.VK_MENU,0,win32con.KEYEVENTF_KEYUP,0)
        time.sleep(.1)
        win32gui.SetForegroundWindow(h)
except Exception as exc:
    lines.append("ERROR="+str(exc))
time.sleep(.8)
front=win32gui.GetForegroundWindow()
lines.append("FG="+str(front)+" title="+win32gui.GetWindowText(front))
ImageGrab.grab(all_screens=False).save(root/"V85_REMIX_SIGNAL_LIVE_ACTIVATED.png")
(root/"V85_NATIVE_ACTIVATE_RESULT.log").write_text("\n".join(lines),encoding="utf8")
