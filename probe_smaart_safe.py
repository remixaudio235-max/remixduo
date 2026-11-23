"""One-time GUI evidence capture; does not touch Smaart generator or settings."""
import time,subprocess
from pathlib import Path
import win32gui,win32con,win32process,psutil
from PIL import ImageGrab
exe=Path(r"C:\Program Files\Smaart Suite\Smaart.exe")
out=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\smaart_964_live_probe.png")
existing=psutil.process_iter(["name"])
if not any((p.info["name"] or "").lower()=="smaart.exe" for p in existing):
  subprocess.Popen([str(exe)],cwd=str(exe.parent))
for _ in range(30):
  result=[]
  def callback(h,unused):
    if "Smaart" in win32gui.GetWindowText(h) and win32gui.IsWindowVisible(h):
       r=win32gui.GetWindowRect(h)
       if r[2]-r[0]>600:result.append((h,r))
  win32gui.EnumWindows(callback,None)
  if result:
    hwnd,r=result[0]
    try: win32gui.SetForegroundWindow(hwnd)
    except Exception as e: print("FRONT_FAIL",type(e).__name__)
    time.sleep(.24)
    ImageGrab.grab().save(out)
    print("SMAART_PROBE_SCREEN",hwnd,r,out,flush=True)
    break
  time.sleep(.15)
else: print("SMAART_WINDOW_NOT_AVAILABLE",flush=True)
