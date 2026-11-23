"""Pixel parity of cached 60Hz pan vs canonical make_geometry at each Y."""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt,QRectF
from PyQt6.QtGui import QPixmap,QPainter,QPainterPath,QPen,QColor
from overlay_v7 import SumGraph
from trf_core import synthetic,compute_sum
from sum_render_v84 import make_geometry
import numpy as np
from PIL import Image
from pathlib import Path
app=QApplication.instance() or QApplication([])
p=Path(__file__).resolve().parent
f=np.geomspace(20,20000,2048)
s=compute_sum(synthetic("A",f,delay_ms=6.3),
              synthetic("B",f,db=-2,delay_ms=7.5))
W,H=740,320
def expected(graph):
    d=graph.data
    val=(d.mag_db+graph.display_offset_db) if graph.kind=="mag" else d.phase_deg
    trusted=np.asarray(d.valid,dtype=bool)
    if graph.kind=="phase" and d.phase_valid is not None:
        trusted&=np.asarray(d.phase_valid,dtype=bool)
    geom=make_geometry(d.hz,val,trusted,graph.f_min,graph.f_max,
                       graph.y_min,graph.y_max,W,H,graph.kind)
    paths={"high":QPainterPath(),"low":QPainterPath()}
    end={"high":None,"low":None}
    for edge in geom.edges:
        q=paths[edge.quality];before=end[edge.quality]
        if (before is None or
            abs(before[0]-edge.x0)>1e-4 or
            abs(before[1]-edge.y0)>1e-4):
            q.moveTo(edge.x0,edge.y0)
        q.lineTo(edge.x1,edge.y1)
        end[edge.quality]=(edge.x1,edge.y1)
    pix=QPixmap(W,H);pix.fill(Qt.GlobalColor.transparent)
    paint=QPainter(pix)
    paint.setClipRect(QRectF(0,0,W,H))
    for quality in ("low","high"):
        paint.setRenderHint(QPainter.RenderHint.Antialiasing,quality=="high")
        c=QColor("#39FF14")
        if quality=="low":c.setAlpha(128)
        paint.setPen(QPen(c,2.0 if quality=="low" else 3.5,
                          Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
        paint.drawPath(paths[quality])
    paint.end()
    return pix
def rgba(pix,path):
    pix.save(str(path))
    return np.asarray(Image.open(path).convert('RGBA'),dtype=np.uint8)
for kind,shifts in (("phase",(0,50,140,-190,245,360)),
                    ("mag",(0,60,150,-160,220))):
    graph=SumGraph(kind)
    graph.resize(W,H)
    graph.roi_guides=False
    graph.require_native_axis=False
    graph.set_data(s)
    graph.show()
    lo,hi=graph.y_min,graph.y_max
    app.processEvents()
    first=None
    for dy in shifts:
        diff=dy*(hi-lo)/H
        graph.y_min=lo+diff;graph.y_max=hi+diff
        observed=rgba(graph.grab(),p/'_qa_v834_current.png')
        goal=rgba(expected(graph),p/'_qa_v834_expected.png')
        # Skip top 35px text label, compare the actual green path only.
        a=(observed[42:-4,:,1]>120)&(observed[42:-4,:,1]>observed[42:-4,:,0]*1.4)
        b=(goal[42:-4,:,1]>120)&(goal[42:-4,:,1]>goal[42:-4,:,0]*1.4)
        tp=np.count_nonzero(a&b)
        prec=tp/max(1,np.count_nonzero(a))
        recall=tp/max(1,np.count_nonzero(b))
        score=(1.0 if (np.count_nonzero(a)==0 and np.count_nonzero(b)==0)
               else 2*prec*recall/max(1e-9,prec+recall))
        print('V834_RASTER_PARITY',kind,dy,
              'F1',round(score,4),'PREC',round(prec,4),
              'RECALL',round(recall,4),'REBUILDS',graph._cache_rebuilds,
              flush=True)
        assert score>.83,(kind,dy,score)
        if first is None:first=graph._cache_rebuilds
        assert graph._cache_rebuilds==first,(kind,dy,'unexpected rebuild')
    graph.close()
print('V834_RASTER_PARITY_ALL_PASS',flush=True)
