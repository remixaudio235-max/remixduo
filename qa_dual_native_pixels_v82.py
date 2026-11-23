from pathlib import Path
import time,win32gui,numpy as np
from PIL import Image
from plot_geometry_v7 import locate_plots
from full_scan_v7 import printwindow_image
from native_fast_pan_v81 import colored_profiles,infer_pan
p=Path(__file__).resolve().parent
h=win32gui.FindWindow(None,"Smaart Suite")
geo=locate_plots(h)
image=printwindow_image(h)
wl,wt,wr,wb=win32gui.GetWindowRect(h)
def roi(rect):
 x,y,w,hh=rect
 # replicate exact NativeFastPan crop
 offset=max(65,int(w*.105))
 width=min(int(w*.65),w-offset-290,440)
 return np.asarray(image.crop((x-wl+offset,y-wt,x-wl+offset+width,y-wt+hh)).convert("RGB"))
for kind,rect in (("phase",geo.phase),("mag",geo.mag)):
 rgb=roi(rect)
 Image.fromarray(rgb).save(p/f"V82_NATIVE_{kind.upper()}_CROP.png")
 base,n=colored_profiles(Image.fromarray(rgb))
 assert n>=300,(kind,n)
 print("NATIVE_ROI",kind,rgb.shape,"pixels",n,flush=True)
 for dy in (-60,-20,-4,-1,0,1,4,19,47,75):
  shifted=np.zeros_like(rgb)
  if dy>0:shifted[dy:]=rgb[:-dy]
  elif dy<0:shifted[:dy]=rgb[-dy:]
  else:shifted[:]=rgb
  target,_=colored_profiles(Image.fromarray(shifted))
  s=time.perf_counter()
  result=infer_pan(base,target)
  elapsed=(time.perf_counter()-s)*1000
  print(kind,"DY",dy,"FOUND",result.delta_px,"VALID",result.valid,"SCORE",round(result.confidence,3),"MS",round(elapsed,1),flush=True)
  assert result.valid and abs(result.delta_px-dy)<=1,(kind,dy,result)
print("V82_NATIVE_BOTH_AXES_PIXEL_QA_PASS",flush=True)
