from pathlib import Path
import numpy as np,time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from trf_core import read_trf,compute_sum
from sum_render_v84 import make_geometry
from overlay_v7 import SumGraph

root=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(root/name) for name in ("4,8 ms delay-1.trf","0 delay-1.trf"))
d=compute_sum(a,b,delay_ms=4.8,coh_gate=.60,mag_oct=1/6,phase_oct=1/6)
m=(d.hz>=650)&(d.hz<=2000)
print("SOURCE_SAMPLES",len(d.hz),"COH_TRUSTED",int(d.valid.sum()),
      "PHASE_SMOOTH_TRUSTED",int(d.phase_valid.sum()),
      "PHASE_FALLBACK_650_2k",int(np.count_nonzero(m & ~d.phase_valid)))
for kind,lo,hi,offset in (("phase",439,799,0),("phase",-251,109,0),
                          ("mag",-80,-44,-63.7),("mag",-21,15,0)):
 v=(d.mag_db+offset) if kind=="mag" else d.phase_deg
 quality=d.valid if kind=="mag" else (d.valid & d.phase_valid)
 t=time.perf_counter()
 g=make_geometry(d.hz,v,quality,20,20000,lo,hi,1442,398,kind)
 print("MODEL_GEOMETRY",kind,"viewport",lo,hi,"edges",len(g.edges),
       "high",g.high_edges,"faint",g.low_edges,
       "wraps",g.wrap_splits,"clipped",g.clipped_edges,"gaps",g.data_gaps,
       "compute_ms",round((time.perf_counter()-t)*1000,2))
 assert g.high_edges>100
 assert g.low_edges>0
 assert all(np.isfinite([e.x0,e.y0,e.x1,e.y1]).all() for e in g.edges)
 assert all(0<=e.y0<=398 and 0<=e.y1<=398 for e in g.edges)
 if kind=="phase":
  assert g.wrap_splits>=6,(kind,g.wrap_splits)
  # All visible segments are short in y; no diagonal across wrapped panel
  assert all(abs(e.y1-e.y0)<250 for e in g.edges)
 if kind=="mag":
  assert g.high_edges+g.low_edges==len(g.edges)
# Analytic +360 wrap test: should reach canvas border, re-enter other side.
f=np.array([100,101,102],float)
phase=np.array([175,-179,-170],float)
gg=make_geometry(f,phase,np.ones(3,bool),20,20000,-180,180,1442,398,"phase")
assert gg.wrap_splits==1 and len(gg.edges)==3,gg
assert any(abs(e.y0-398)<1e-6 or abs(e.y1-398)<1e-6 for e in gg.edges)
assert any(abs(e.y0)<1e-6 or abs(e.y1)<1e-6 for e in gg.edges)
assert max(abs(e.y1-e.y0) for e in gg.edges)<30
print("PHASE_WRAP_TO_BORDERS_NO_DIAGONAL_PASS",gg)
# Magnitude segment from out-of-range value into view is clipped not dropped.
mg=make_geometry(np.array([100.,101.]),np.array([30.,0.]),
    np.ones(2,bool),20,20000,-10,10,1442,398,"mag")
assert len(mg.edges)==1 and (abs(mg.edges[0].y0)<1e-6)
print("MAG_Y_CLIP_CROSSING_PASS",mg.edges[0])
app=QApplication([])
for kind,lo,hi,offset in (("phase",439,799,0),("mag",-80,-44,-63.7)):
 widget=SumGraph(kind)
 widget.setGeometry(0,0,1442,398)
 widget.y_min,widget.y_max=lo,hi
 widget.display_offset_db=offset
 widget.set_data(d)
 elapsed=[]
 for i in range(16):
  im=QImage(1442,398,QImage.Format.Format_ARGB32)
  im.fill(0)
  t=time.perf_counter()
  widget.render(im)
  elapsed.append((time.perf_counter()-t)*1000)
  if i==0:
   out=f"V84_SUM_{kind.upper()}_RENDER_QA.png"
   assert im.save(out)
 print("QT_PAINT",kind,"P50",round(np.percentile(elapsed[1:],50),2),
       "P95",round(np.percentile(elapsed[1:],95),2),
       "first",round(elapsed[0],2),
       "drawn_segments",widget._last_points,
       "weak",widget._last_low_coh,"wraps",widget._last_wraps,
       "clipped",widget._last_clipped)
 assert widget._last_points>150
 widget.close()
app.processEvents()
print("V84_SUM_CONTINUITY_QA_ALL_PASS")
