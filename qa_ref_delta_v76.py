from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import QApplication
from trf_core import (read_trf,matched,auto_align,phase_match_percent,
                      compute_sum,sum_ref_phase_delta,synthetic)
from overlay_v7 import App
folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(folder/n) for n in ("4,8 ms delay-1.trf","0 delay-1.trf"))
delta1,p951,n1=sum_ref_phase_delta(a,b,delay_ms=4.8,
                                 lf=60,hf=527.2)
delta2,p952,n2=sum_ref_phase_delta(b,a,delay_ms=-4.8,
                                 lf=60,hf=527.2)
print("PHYSICAL_PAIR",a.path.name,b.path.name)
print("REF1_DELTA",delta1,p951,n1)
print("REF2_DELTA",delta2,p952,n2)
assert n1>=100 and n1==n2
assert 0<delta1<6 and 0<delta2<6
p1,_=phase_match_percent(a,b,delay_ms=4.8,lf=60,hf=527.2)
p2,_=phase_match_percent(b,a,delay_ms=-4.8,lf=60,hf=527.2)
assert abs(p1-p2)<1e-8
print("REF_INVARIANT_MATCH_PERCENT",p1,p2)
sm1=compute_sum(a,b,delay_ms=4.8)
sm2=compute_sum(b,a,delay_ms=-4.8)
assert np.allclose(sm1.hz,sm2.hz)
assert np.allclose(sm1.mag_db,sm2.mag_db,atol=1e-8)
print("REF_SWAP_MAG_INVARIANT_PASS",len(sm1.hz))
# Inverted trace test ensures correctness even when source polarization differs.
f=np.geomspace(50.,4000.,350)
ref=synthetic("REF",f)
other=synthetic("OTHER",f,delay_ms=-3.2,invert=True)
r=auto_align(ref,other,lf=80,hf=800,max_delay_ms=12)
assert r and abs(r[0].delay_ms-3.2)<.11 and r[0].invert_trace2
inverted_delta,p95,n=sum_ref_phase_delta(ref,other,delay_ms=3.2,
    invert_other=True,lf=80,hf=800)
assert inverted_delta<1e-6
print("INV_CORRECTION_REF1_PASS",inverted_delta)
rev=auto_align(other,ref,lf=80,hf=800,max_delay_ms=12)
assert rev and abs(rev[0].delay_ms+3.2)<.11 and rev[0].invert_trace2
reversed_delta,p95,n=sum_ref_phase_delta(other,ref,delay_ms=-3.2,
    invert_other=True,lf=80,hf=800)
assert reversed_delta<1e-6
print("INV_CORRECTION_REF2_PASS",reversed_delta)
# No evidence -> "--" not 0; cancellation means sum phase undefined.
a0=synthetic("a0",f)
b0=synthetic("b0",f)
none95=sum_ref_phase_delta(a0,b0,invert_other=True,lf=80,hf=800)
assert none95[0] is None,none95
print("PHASE_UNDEFINED_CANCEL_PASS",none95)
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
gui.current_traces=(a,b)
gui.recalc()
gui.delay.setValue(4.8)
gui.hf.setValue(527.2)
assert gui._reference_index()==0
assert gui._ordered_traces()==(a,b)
assert abs(float(gui.graph_phase.phase_match_value)-p1)<1e-4
assert f"{delta1:.2f}°" in gui.sum_ref_label.text(),gui.sum_ref_label.text()
print("GUI_REF1",gui.correction_target_label.text(),gui.phase_match_label.text(),gui.sum_ref_label.text())
mag_before=gui.current_sum.mag_db.copy()
gui.last_solve=[object()]
gui.ref_choice.setCurrentIndex(1)
assert gui._reference_index()==1
assert gui._ordered_traces()==(b,a)
assert abs(gui.delay.value()+4.8)<.00001
assert gui.last_solve is None and all(x.text()=="-" for x in gui.candidates)
assert np.allclose(gui.current_sum.mag_db,mag_before)
assert abs(gui.graph_phase.phase_match_value-p2)<1e-5
assert f"{delta2:.2f}°" in gui.sum_ref_label.text(),gui.sum_ref_label.text()
assert "TRACE 1" in gui.invert.text()
print("GUI_REF2",gui.correction_target_label.text(),gui.phase_match_label.text(),gui.sum_ref_label.text(),gui.delay.value())
# AUTO ALIGN on REF2 should solve -4.8ms on Trace1, unlike REF1 +4.8ms.
gui.align()
assert gui.last_solve
best=gui.last_solve[0]
assert abs(best.delay_ms+4.8)<.11 and not best.invert_trace2,(best.delay_ms,best.invert_trace2)
assert "SHIFT T1" in gui.candidates[0].text()
assert abs(gui.delay.value()+4.8)<.11
print("AUTO_ALIGN_REF2_PASS",best.delay_ms,best.score_db,gui.candidates[0].text())
gui.ref_choice.setCurrentIndex(0)
assert gui.delay.value()>4.7 and gui._ordered_traces()==(a,b)
gui.align()
assert abs(gui.last_solve[0].delay_ms-4.8)<.11
print("AUTO_ALIGN_REF1_PASS",gui.delay.value(),gui.candidates[0].text())
# Editing ROI without running AutoAlign updates circular diagnostic only.
sum_id=id(gui.current_sum)
gui.lf.setValue(75.0)
assert id(gui.current_sum)==sum_id
assert gui.last_solve is None
assert "Δ SUM–REF:" in gui.sum_ref_label.text()
print("ROI_DELTA_LIVE_PASS",gui.sum_ref_label.text())
gui.close()
app.processEvents()
print("V76_REF_DELTA_FULL_QA_PASS")
