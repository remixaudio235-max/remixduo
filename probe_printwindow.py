from pathlib import Path
import ctypes,win32gui,win32ui,win32con
from PIL import Image
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\smaart_printwindow.png")
hwnd=0
def cb(h,_):
 global hwnd
 if win32gui.IsWindowVisible(h) and "Smaart Suite" in win32gui.GetWindowText(h):
  rect=win32gui.GetWindowRect(h)
  if rect[2]-rect[0]>650:hwnd=h
win32gui.EnumWindows(cb,None)
if not hwnd:raise RuntimeError("Smaart main window absent")
r=win32gui.GetWindowRect(hwnd);w,h=r[2]-r[0],r[3]-r[1]
hdc=win32gui.GetWindowDC(hwnd)
src=win32ui.CreateDCFromHandle(hdc)
dst=src.CreateCompatibleDC()
bmp=win32ui.CreateBitmap();bmp.CreateCompatibleBitmap(src,w,h)
dst.SelectObject(bmp)
rc=ctypes.windll.user32.PrintWindow(hwnd,dst.GetSafeHdc(),2)
image=Image.frombuffer("RGB",(w,h),bmp.GetBitmapBits(True),"raw","BGRX",0,1)
image.save(p)
import numpy as np
colors=np.asarray(image)
print("PRINTWINDOW",hwnd,rc,(w,h),"RGB_MEAN",colors.mean(axis=(0,1)),"VAR",colors.var(),"file",p)
win32gui.DeleteObject(bmp.GetHandle())
dst.DeleteDC();src.DeleteDC();win32gui.ReleaseDC(hwnd,hdc)
