"""Offscreen-only MagFIR/PhaseFIR render P95, not live mouse latency."""
import os
os.environ["QT_QPA_PLATFORM"]="offscreen"
from time import perf_counter
import numpy as np
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from test_v846_fir_native import source,frame,MAG,PHASE
from fir_native_v846 import rasterize_fir_frame

def bench():
    app=QApplication.instance() or QApplication([])
    src,_=source()
    fr=rasterize_fir_frame(src,frame(src))
    engine=App(False)
    engine.timer.stop()
    results={}
    try:
        for kind,graph,rect in (("mag",engine.graph_mag,MAG),
                                ("phase",engine.graph_phase,PHASE)):
            graph.setGeometry(*rect)
            graph.set_fir(src,fr)
            graph.show()
            app.processEvents()
            measures=[]
            for _ in range(40):
                start=perf_counter()
                graph.update()
                app.processEvents()
                measures.append((perf_counter()-start)*1000)
            results[kind]=(float(np.median(measures)),
                           float(np.percentile(measures,95)),
                           max(measures))
            graph.hide()
            graph.set_fir()
        for name,values in results.items():
            print("FIR_PAINT",name,"N",40,"P50_MS",round(values[0],2),
                  "P95_MS",round(values[1],2),"MAX_MS",round(values[2],2),flush=True)
        assert all(v[1]<33.33 for v in results.values()),"P95 FIR offscreen"
    finally:
        engine.graph_mag.close()
        engine.graph_phase.close()
        engine.close()
if __name__=="__main__":bench()
