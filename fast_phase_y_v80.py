"""Fast native Phase Y capture path, pixel-level read only.

Thread-owned, reusable Win32 GDI desktop ROI capture is fast when original
Smaart is visible. It includes the green RemiX overlay (excluded by color
mask) but never reads or changes Smaart's memory, audio or configuration.
If desktop pixels do not validate, fall back to native PrintWindow at a
restricted rate. Never report source parity without REF fit acceptance.
"""
from __future__ import annotations
from dataclasses import dataclass
from PIL import Image
import threading,time
import win32gui,win32ui,win32con
from phase_axis_absolute_v79 import fit_ref_phase_axis,capture_fit,AxisFit

_tls=threading.local()

class DesktopRoiCapture:
    def __init__(self):
        self.hdc=win32gui.GetDC(0)
        self.desktop=win32ui.CreateDCFromHandle(self.hdc)
        self.mem=self.desktop.CreateCompatibleDC()
        self.bitmap=None
        self.old=None
        self.size=None
    def capture(self,x,y,w,h):
        if (w,h)!=self.size:
            if self.bitmap is not None:
                self.mem.SelectObject(self.old)
                win32gui.DeleteObject(self.bitmap.GetHandle())
            self.bitmap=win32ui.CreateBitmap()
            self.bitmap.CreateCompatibleBitmap(self.desktop,w,h)
            self.old=self.mem.SelectObject(self.bitmap)
            self.size=(w,h)
        self.mem.BitBlt((0,0),(w,h),self.desktop,(x,y),win32con.SRCCOPY)
        return Image.frombytes("RGB",(w,h),self.bitmap.GetBitmapBits(True),"raw","BGRX")
    def close(self):
        if self.bitmap is not None:
            self.mem.SelectObject(self.old)
            win32gui.DeleteObject(self.bitmap.GetHandle())
            self.bitmap=None
        self.mem.DeleteDC()
        self.desktop.DeleteDC()
        win32gui.ReleaseDC(0,self.hdc)

@dataclass(frozen=True)
class FastFitResult:
    fit:AxisFit
    elapsed_ms:float
    mode:str
    frame_time:float

def capture_fit_fast(hwnd,phase_rect,ref,other,center_top):
    start=time.perf_counter()
    x,y,w,h=map(int,phase_rect)
    # Desktop coordinates must be valid and visible. If a window obscures
    # the graph, the native colored REF comparison fails closed.
    mode="gdi"
    try:
        dc=getattr(_tls,"desktop_roi",None)
        if dc is None:
            dc=DesktopRoiCapture()
            _tls.desktop_roi=dc
        im=dc.capture(x,y,w,h)
        fit=fit_ref_phase_axis(im,(0,0,w,h),(0,0,w,h),
                              ref,other,center_top=center_top)
    except Exception:
        fit=AxisFit(0.,0.,0.,0.,0,False,"GDI capture failed")
    # Only attempt slow fallback when image content is not validated.
    if not fit.accepted:
        mode="printwindow"
        try:
            fit=capture_fit(hwnd,phase_rect,ref,other,center_top=center_top)
        except Exception as exc:
            fit=AxisFit(0.,0.,0.,0.,0,False,str(exc)[:70])
    elapsed=(time.perf_counter()-start)*1000
    return FastFitResult(fit,elapsed,mode,time.monotonic())
