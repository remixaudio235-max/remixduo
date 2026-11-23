from pathlib import Path
from PIL import Image
import numpy as np
p=Path(__file__).resolve().parent
names=['_qa_phase_gui_drag_down.png','_qa_phase_gui_restored.png']
im=[np.asarray(Image.open(p/n).convert('RGB'),dtype=np.uint8) for n in names]
# Isolate neon SUM green, excluding the LF/HF guide + phase-match text regions.
def mask(z,mode):
 a=z[140:500,500:1070].astype(np.int16)
 r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
 if mode=='green':
  return (g>185)&(g>r*1.7)&(g>b*1.7)&(r<170)&(b<160)
 return (b>88)&(b>r*1.5)&(b>g*1.4)&(g<160)
def score(x,y,dy):
 if dy>0:a,b=x[:-dy],y[dy:]
 elif dy<0:a,b=x[-dy:],y[:dy]
 else:a,b=x,y
 return float(np.count_nonzero(a&b)/np.sqrt(max(1,int(a.sum())*int(b.sum()))))
for mode in ('green','blue'):
 a,b=(mask(z,mode) for z in im)
 q=sorted([(score(a,b,dy),dy) for dy in range(-100,101)],reverse=True)[:8]
 print('RASTER',mode,'PIXELS',int(a.sum()),int(b.sum()),'TOPSHIFTS',q,flush=True)
