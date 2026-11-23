from pathlib import Path
from PIL import Image
import numpy as np
from plot_geometry_v7 import locate_plots
import win32gui
h=win32gui.FindWindow(None,"Smaart Suite")
geo=locate_plots(h)
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_11_AUTO_SMOOTH_COMPACT_QA\V812_BASE_SMAART_SCREEN.png")
pix=np.asarray(Image.open(p).convert("RGB"))
rects=[geo.phase,geo.mag]
def binary(rect,width):
 x,y,w,h=rect
 patch=pix[y+5:y+19,x+13:x+13+width]
 return ((np.min(patch,axis=2)>150) & ((np.max(patch,axis=2)-np.min(patch,axis=2))<35)).astype(float)
mag=binary(rects[0],84)
phase=binary(rects[1],52)
for i,r in enumerate(rects):
 for tag,template in (("mag",mag),("phase",phase)):
  c=binary(r,template.shape[1])
  score=(c*template).sum()/np.sqrt((c*c).sum()*(template*template).sum())
  print("REGION",i,tag,"sim",round(score,4),"bright",int(c.sum()),"template_white",int(template.sum()),flush=True)
dest=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_11_AUTO_SMOOTH_COMPACT_QA")
Image.fromarray(np.uint8(mag*255)).save(dest/"V812_MAG_TITLE_TEMPLATE.png")
Image.fromarray(np.uint8(phase*255)).save(dest/"V812_PHASE_TITLE_TEMPLATE.png")
