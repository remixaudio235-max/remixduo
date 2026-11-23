from pathlib import Path
from pywinauto import Desktop
from PIL import Image
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from selection_v7 import archive_order,scan_icon_white_cross
from full_scan_v7 import printwindow_image
w=Desktop(backend="uia").window(title="Smaart Suite")
b=w.descendants(control_type="ScrollBar")[0]
r=b.iface_range_value
start=r.CurrentValue
try:
 r.SetValue(900)
 time.sleep(.16)
 img=printwindow_image(w.handle)
 img.crop((0,250,205,650)).resize((410,800)).save(Path(__file__).resolve().parent/"qa_missing_rows.png")
 order=archive_order(Path.home()/r"Documents\Smaart Suite\Data\Transfer Function\Session Data")
 for i in [49,50,51,52,53,54]:
  y=163+i*22-r.CurrentValue
  box=(16,int(y+3),31,int(y+18))
  cut=img.crop(box)
  import numpy as np
  rgb=np.asarray(cut).astype(float)/255.
  hi=rgb.max(axis=2);lo=rgb.min(axis=2)
  white=((lo>.66)&((hi-lo)<.2)).mean()
  color=((hi>.13)&((hi-lo)>.07)).mean()
  print("ROW",i,order[i].name,"y",y,"WHITE",round(white,3),"COLOR",round(color,3),"STATE",scan_icon_white_cross(img,box))
finally:
 r.SetValue(start);print("RESTORED",r.CurrentValue)
