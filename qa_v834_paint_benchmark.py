"""Offline Qt paint P95 under viewport translation; 4096 complex TF bins."""
from PyQt6.QtWidgets import QApplication
from overlay_v7 import SumGraph
from trf_core import synthetic,compute_sum
import numpy as np,time

app=QApplication.instance() or QApplication([])
freq=np.geomspace(20,20000,4096)
a=synthetic("A",freq,db=-2,delay_ms=6.4)
b=synthetic("B",freq,db=1,delay_ms=7.6)
summed=compute_sum(a,b)
for kind in ('phase','mag'):
 graph=SumGraph(kind)
 graph.setGeometry(250,100,1442,412)
 graph.require_native_axis=False
 graph.set_data(summed)
 graph.show()
 app.processEvents()
 lo,hi=graph.y_min,graph.y_max
 times=[]
 for k in range(45):
  shift=((k%16)-8)*14.
  d=shift*(hi-lo)/412.
  graph.y_min,graph.y_max=lo+d,hi+d
  start=time.perf_counter()
  graph.grab()
  app.processEvents()
  times.append((time.perf_counter()-start)*1000.)
 arr=np.asarray(times[5:])
 print('BENCH',kind,'N',len(arr),'P50_MS',round(float(np.median(arr)),2),
       'P95_MS',round(float(np.percentile(arr,95)),2),
       'MAX_MS',round(float(np.max(arr)),2),
       'DRAW_CALLS',graph.draw_count,'SEGMENTS',graph._last_points,
       flush=True)
 graph.hide();graph.close()
