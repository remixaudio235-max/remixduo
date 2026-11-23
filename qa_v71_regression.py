from pathlib import Path
from types import SimpleNamespace
from PIL import Image,ImageDraw
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from selection_v7 import archive_order
from full_scan_v7 import _page
from smaart_axes_v71 import read_saved_axes
from trf_core import read_trf,compute_sum
from overlay_v7 import SumGraph
import numpy as np,os

root=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
order=archive_order(root)
assert len(order)==106 and order[0].name=="TUNNINNGGG-8.trf"
axes=read_saved_axes()
assert axes["mag"]==(-80.,-44.),axes
print("PASS index.xml source IDs 0..105 and axes",axes)

class Row:
    def __init__(self,i):self.i=i
    def rectangle(self):
        return SimpleNamespace(top=90+self.i*22,left=9)
rows={i:Row(i) for i in range(45)}
for pair in ((20,21),(21,22),(0,1)):
    canvas=Image.new("RGB",(230,1150),(14,19,26))
    d=ImageDraw.Draw(canvas)
    for i in rows:
        x,y=16,90+i*22+3
        d.rectangle((x,y,x+14,y+14),fill=(18,170,235))
        if i not in pair:
            d.line((x+2,y+2,x+12,y+12),fill=(255,255,255),width=2)
            d.line((x+12,y+2,x+2,y+12),fill=(255,255,255),width=2)
    states=_page(canvas,[None]*45,0,0,85,1150,0,22,
                uia_rows=rows,window_origin=(0,0))
    active=tuple(i for i,v in sorted(states.items()) if v=="on")
    assert active==pair,(pair,active)
    print("PASS exact native row index pair",pair)

a,b=(read_trf(root/x) for x in ("subb-1.trf","fullh-1.trf"))
s=compute_sum(a,b)
mag=s.mag_db[(s.hz>=20)&(s.hz<=20000)]
mid=sum(axes["mag"])/2
shift=round(mid-float(np.median(mag)),1)
projected=s.mag_db+shift
actual_visible=int(np.sum((s.mag_db>=-80)&(s.mag_db<=-44)))
preview_visible=int(np.sum((projected>=-80)&(projected<=-44)))
assert preview_visible>=300,(preview_visible,actual_visible)
print("PASS Mag display-only shift",shift,"visible",preview_visible,"of",len(s.hz),
      "native_visible",actual_visible,"low_coh",int(np.sum(~s.valid)))
app=QApplication([])
graph=SumGraph("mag")
graph.setGeometry(0,0,1200,400)
graph.y_min,graph.y_max=axes["mag"]
graph.display_offset_db=shift
graph.set_data(s)
img=QImage(1200,400,QImage.Format.Format_ARGB32)
img.fill(0)
graph.render(img)
out=Path("V71_REAL_MODEL_MAG_QA.png")
assert img.save(str(out))
assert graph._last_points>=300,graph._last_points
assert graph._last_low_coh>0
print("PASS QT_MAG_RENDER",graph._last_points,"low_coh",graph._last_low_coh,
      "file",out.resolve())
