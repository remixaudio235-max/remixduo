from PIL import Image
import numpy as np
img=Image.open(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\smaart_printwindow.png").convert("RGB")
for row in (0,7,49,50,51,53,54):
 y=163+row*22 if row<30 else 163+row*22-900
 if row<30:
  # need original top screenshot
  pass
 else:
  img2=Image.open(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\qa_missing_rows.png")
  # screenshot is cropped from (0,250) and scaled 2; use PNG scaled
  # easier recapture original current pos 900 in test manually; skip.
  continue
 crop=np.asarray(img.crop((16,int(y+3),31,int(y+18))),dtype=float)/255
 v=crop.mean(axis=2)
 Y,X=np.indices(v.shape)
 inner=(X>=2)&(X<=12)&(Y>=2)&(Y<=12)
 cross=((abs(X-Y)<=1)|(abs((X+Y)-14)<=1))&inner
 non=inner&(~cross)
 print(row,"diag",v[cross].mean(),"offdiag",v[non].mean(),"contrast",v[cross].mean()-v[non].mean())
