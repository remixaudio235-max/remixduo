from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage
from trf_core import synthetic,phase_match_percent,read_trf,auto_align,compute_sum
from overlay_v7 import App,SumGraph
from roi_markers_v73 import hz_to_x
import time

f=np.geomspace(30,10000,400)
a=synthetic("a",f)
same=synthetic("same",f)
opposite=synthetic("opposite",f,invert=True)
quarter=synthetic("quarter",f,delay_ms=0)  # replace with uniform +90 deg
quarter=type(quarter)(quarter.name,quarter.path,quarter.hz,1j*quarter.h,
                       quarter.coherence,quarter.kind,quarter.file_mtime_ns)
for target,expect in ((same,100),(opposite,0),(quarter,50)):
    pct,n=phase_match_percent(a,target,lf=50,hf=3000)
    assert n>12 and abs(pct-expect)<0.000001,(pct,n,expect)
    print("PASS_NORMALIZED_SCORE",expect,"actual",pct,"valid_bins",n)
aligned=synthetic("delayed",f,delay_ms=4.2)
bad,n=phase_match_percent(a,aligned,lf=100,hf=1000)
fixed,n=phase_match_percent(a,aligned,delay_ms=-4.2,lf=100,hf=1000)
assert fixed>99.999 and bad<95,(fixed,bad)
print("PASS_DELAY_DEPENDENCY",round(bad,3),"to",round(fixed,3))
invert,n=phase_match_percent(a,opposite,invert_trace2=True)
assert invert>99.999
print("PASS_INVERSION_DEPENDENCY")
c=np.full(len(f),0.2)
low=type(a)(a.name,a.path,a.hz,a.h,c,a.kind,a.file_mtime_ns)
pct,n=phase_match_percent(low,same,coh_gate=.6)
assert pct is None and n==0
print("PASS_NO_FALSE_100_PERCENT_WHEN_LOW_COHERENCE")
pct,n=phase_match_percent(a,same,lf=50,hf=52,min_bins=12)
assert pct is None and n<12
print("PASS_NO_FALSE_100_PERCENT_WHEN_TOO_FEW_BINS",n)

folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
paths=[folder/"TUNNINNGGG-8.trf",folder/"TUNNINNGGG-7.trf"]
if not all(p.exists() for p in paths):
    paths=sorted(folder.glob("*.trf"))[:2]
trace=tuple(read_trf(p) for p in paths)
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
gui.current_traces=trace
gui.recalc()
assert gui.graph_phase.phase_match_value is not None
a_match=gui.graph_phase.phase_match_value
assert "PHASE MATCH:" in gui.phase_match_label.text(),gui.phase_match_label.text()
print("PASS_GUI_MATCH_INIT",gui.phase_match_label.text())
raw_id=id(gui.current_sum)
gui.plot_layout=type("Rect",(),{"phase":(252,112,1442,398),"mag":(252,553,1442,398)})()
gui._apply_plot_layout()
gui.lf.setValue(75.0)
gui.hf.setValue(400.0)
assert id(gui.current_sum)==raw_id,"Dragging ROI must not recalculate physical SUM"
direct,n=phase_match_percent(*trace,lf=75,hf=400,delay_ms=gui.delay.value(),invert_trace2=False)
assert abs(direct-gui.graph_phase.phase_match_value)<1e-10
assert gui.graph_phase.phase_match_bins==n
print("PASS_LIVE_ROI_SYNC_NO_SOLVER_RECALC",gui.phase_match_label.text())
gui.invert.setChecked(True)
inv=gui.graph_phase.phase_match_value
direct_inv,n=phase_match_percent(*trace,lf=75,hf=400,invert_trace2=True)
assert abs(inv-direct_inv)<1e-10
assert abs(inv-(100-direct))<.001
print("PASS_LIVE_INVERT_UPDATES_PERCENT",gui.phase_match_label.text())
gui.delay.setValue(3.0)
direct_delay,n=phase_match_percent(*trace,delay_ms=3.0,lf=75,hf=400,invert_trace2=True)
assert abs(direct_delay-gui.graph_phase.phase_match_value)<1e-10
print("PASS_LIVE_DELAY_UPDATES_PERCENT",gui.phase_match_label.text())
gui.graph_phase.set_data(gui.current_sum)
gui.graph_mag.set_data(gui.current_sum)
for kind,graph in (("phase",gui.graph_phase),("mag",gui.graph_mag)):
    image=QImage(1442,398,QImage.Format.Format_ARGB32)
    image.fill(0)
    graph.render(image)
    assert image.save(f"V74_{kind.upper()}_GREEN_MATCH_QA.png")
    data=image.convertToFormat(QImage.Format.Format_RGBA8888)
    ptr=data.bits();ptr.setsize(data.sizeInBytes())
    pixels=np.frombuffer(ptr, np.uint8).reshape((398,data.bytesPerLine()))[:,:1442*4].reshape((398,1442,4))
    green=(pixels[:,:,1]>180) & (pixels[:,:,0]<130) & (pixels[:,:,2]<130) & (pixels[:,:,3]>60)
    assert int(green.sum())>600,(kind,int(green.sum()))
    print("PASS_NEON_GREEN_RENDER",kind,int(green.sum()),"green_pixels")
# Actual Auto Align still uses LF-HF without changing solver.
gui.delay.setValue(0.0)
gui.invert.setChecked(False)
base=auto_align(*trace,lf=gui.lf.value(),hf=gui.hf.value())
gui.align()
assert gui.last_solve and len(gui.last_solve)==len(base)
assert abs(gui.last_solve[0].delay_ms-base[0].delay_ms)<1e-8
assert abs(gui.graph_phase.phase_match_value-phase_match_percent(
    *trace,lf=gui.lf.value(),hf=gui.hf.value(),delay_ms=gui.delay.value(),
    invert_trace2=gui.invert.isChecked())[0])<1e-10
print("PASS_AUTO_ALIGN_DEPENDENCY",gui.phase_match_label.text())
gui.close()
app.processEvents()
print("V74_QA_ALL_PASS")
