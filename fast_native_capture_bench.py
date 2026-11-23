from PIL import Image
import win32gui,win32ui,win32con
class DesktopRoiCapture:
 def __init__(self):
  self.dc_handle=win32gui.GetDC(0)
  self.dc=win32ui.CreateDCFromHandle(self.dc_handle)
  self.mem=self.dc.CreateCompatibleDC()
  self.bitmap=None;self.size=None
 def capture(self,x,y,w,h):
  if self.size!=(w,h):
   if self.bitmap:
    self.mem.SelectObject(self.old)
    win32gui.DeleteObject(self.bitmap.GetHandle())
   self.bitmap=win32ui.CreateBitmap()
   self.bitmap.CreateCompatibleBitmap(self.dc,w,h)
   self.old=self.mem.SelectObject(self.bitmap)
   self.size=(w,h)
  self.mem.BitBlt((0,0),(w,h),self.dc,(x,y),win32con.SRCCOPY)
  bits=self.bitmap.GetBitmapBits(True)
  return Image.frombytes("RGB",(w,h),bits,"raw","BGRX")
 def close(self):
  if self.bitmap:
   self.mem.SelectObject(self.old)
   win32gui.DeleteObject(self.bitmap.GetHandle())
  self.mem.DeleteDC()
  self.dc.DeleteDC()
  win32gui.ReleaseDC(0,self.dc_handle)
if __name__=="__main__":
 import time,numpy as np
 from phase_axis_absolute_v79 import capture_fit,fit_ref_phase_axis
 from trf_core import read_trf
 from pathlib import Path
 from plot_geometry_v7 import locate_plots
 h=win32gui.FindWindow(None,"Smaart Suite")
 x,y,w,hh=locate_plots(h).phase
 d=DesktopRoiCapture()
 p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
 a=read_trf(p/"4,8 ms delay-1.trf");b=read_trf(p/"0 delay-1.trf")
 capture_times=[];fit_times=[]
 for i in range(20):
  t=time.perf_counter()
  im=d.capture(x,y,w,hh)
  capture_times.append((time.perf_counter()-t)*1000)
  t=time.perf_counter()
  fit=fit_ref_phase_axis(im,(0,0,w,hh),(0,0,w,hh),a,b,center_top=180)
  fit_times.append((time.perf_counter()-t)*1000)
  assert fit.accepted,(i,fit)
  if i==0:im.save("V80_GDI_NATIVE_CAPTURE.png")
 print("GDI_CAPTURE_MS",np.round(capture_times,1).tolist(),"mean",np.mean(capture_times),"p95",np.percentile(capture_times,95))
 print("FIT_MS",np.round(fit_times,1).tolist(),"mean",np.mean(fit_times),"p95",np.percentile(fit_times,95),"lastfit",fit)
 d.close()
