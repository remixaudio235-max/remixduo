"""Compare native Mag and SUM after a non-moving Y ruler gesture."""
from pathlib import Path
from PIL import Image
import numpy as np
p=Path(__file__).resolve().parent
a=np.asarray(Image.open(p/'V834_MAG_PRE.png').convert('RGB'),dtype=np.int16)
b=np.asarray(Image.open(p/'V834_MAG_PEAK.png').convert('RGB'),dtype=np.int16)
r=(slice(630,910),slice(460,1100))
def mask(img,kind):
 z=img[r]
 R,G,B=z[:,:,0],z[:,:,1],z[:,:,2]
 if kind=='red':return (R>170)&(R>G*2)&(R>B*2)
 return (G>165)&(G>R*1.5)&(G>B*1.5)&(R<150)
for kind in ('red','green'):
 aa=mask(a,kind);bb=mask(b,kind)
 intersection=int(np.count_nonzero(aa&bb))
 union=int(np.count_nonzero(aa|bb))
 iou=intersection/max(1,union)
 print('V834_NO_GHOST',kind,'IOU',round(iou,4),
       'PIXELS',int(aa.sum()),int(bb.sum()),flush=True)
 assert iou>.87,(kind,iou)
