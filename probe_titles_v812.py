from PIL import Image
from pathlib import Path
from plot_geometry_v7 import locate_plots
import win32gui,numpy as np
h=win32gui.FindWindow(None,"Smaart Suite")
geo=locate_plots(h)
print("LIVE_GEOMETRY",geo)
im=np.asarray(Image.open(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_11_AUTO_SMOOTH_COMPACT_QA\V812_BASE_SMAART_SCREEN.png").convert("RGB"))
for label,rect in [("TOP_DEFAULT_PHASE",geo.phase),("BOTTOM_DEFAULT_MAG",geo.mag)]:
 x,y,w,ht=rect
 print(label,"RECT",rect)
 for ry in range(-5,29):
  pix=im[y+ry,x+12:x+125,:]
  white=(np.min(pix,axis=1)>155) & ((np.max(pix,axis=1)-np.min(pix,axis=1))<40)
  count=int(white.sum())
  if count>8:print("ROW",ry,"WHITES",count)
 for ry in range(0,24):
  p=im[y+ry,x+14:x+105,:]
  white=(np.min(p,axis=1)>170)&((np.max(p,axis=1)-np.min(p,axis=1))<30)
  print("MASK",ry,"".join("#" if k else " " for k in white[::2]))
