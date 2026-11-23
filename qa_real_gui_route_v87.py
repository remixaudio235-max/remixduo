"""V8.7 real-trace and Qt UI QA, no direct Smaart or DSP writes."""
from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import QApplication
from trf_core import read_trf,auto_align
from positive_delay_route_v87 import route_candidate
from overlay_v7 import App

root=Path(__file__).resolve().parent
data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
pairs=(("SUb.trf","FULL.trf"),("4,8 ms delay-1.trf","0 delay-1.trf"))
app=QApplication([])
w=App(demo=False)
w.timer.stop()
w.show()
app.processEvents()
assert w.delay.minimum()==0 and w.delay.maximum()==180
assert "TRỄ T2" in w.delay_route_label.text()
assert "ĐẢO TRACE 2"==w.invert.text()
for first,second in pairs:
 a,b=read_trf(data/first),read_trf(data/second)
 w.current_pair=(str(a.path),str(b.path))
 w.current_traces=(a,b)
 w.pair_label.setText("01 "+a.path.stem+"\n02 "+b.path.stem)
 w.ref_choice.blockSignals(True);w.ref_choice.setCurrentIndex(0);w.ref_choice.blockSignals(False)
 w.lf.setValue(60)
 w.hf.setValue(200)
 w.recalc()
 results=auto_align(a,b,lf=60,hf=200,max_delay_ms=180)
 assert len(results)>=1
 expected=route_candidate(results[0])
 print("REAL_PAIR",first,second,
       "RAW_SIGNED",round(results[0].delay_ms,2),
       "ROUTED",expected,flush=True)
 w.align()
 assert w.ref_choice.currentIndex()==expected.reference_index
 assert w.delay.value()>=0
 assert abs(w.delay.value()-expected.delay_ms)<.06
 assert w.invert.isChecked()==expected.invert_target
 assert f"TRỄ T{expected.delay_trace}" in w.delay_route_label.text()
 assert f"ĐẢO TRACE {expected.delay_trace}"==w.invert.text()
 assert f"GIỮ T{expected.reference_trace}" in w.delay_route_label.text()
 assert w.current_sum is not None
 assert w.last_solve
 assert all("TRỄ T" in label.text() for label in w.candidates[:3])
 first_route=(w.ref_choice.currentIndex(),w.delay.value(),w.invert.isChecked())
 first_mag=w.current_sum.mag_db.copy()
 first_phase_score=w.phase_match_label.text()
 w.align()
 after=(w.ref_choice.currentIndex(),w.delay.value(),w.invert.isChecked())
 assert after==first_route,(first,after,first_route)
 assert np.allclose(w.current_sum.mag_db,first_mag)
 assert w.phase_match_label.text()==first_phase_score
 print("REAL_PAIR_REPEAT_ALIGN_STABLE_PASS",first,after,first_phase_score,flush=True)
 if first=="SUb.trf":
  assert expected.delay_trace==1,expected
  assert expected.delay_ms>0
  img=root/"REMIX_SIGNAL_V87_SUB_FULL_RESULT.png"
  assert w.grab().save(str(img))
  print("REAL_SUB_FULL_GUI_IMAGE",img,flush=True)
# Test manual delay bounds (no negative possible); ref toggle leaves positive.
w.delay.setValue(-10)
assert w.delay.value()==0
w.delay.setValue(4.50)
w.ref_choice.setCurrentIndex(1-w.ref_choice.currentIndex())
assert w.delay.value()==4.50
assert "TRỄ T" in w.delay_route_label.text()
print("POSITIVE_MANUAL_DELAY_AND_REF_SWITCH_PASS")
for i in range(w.tabs.count()):
 w.tabs.setCurrentIndex(i)
 app.processEvents()
 file=root/f"REMIX_SIGNAL_V87_TAB_{i}.png"
 assert w.grab().save(str(file))
 print("GUI_IMAGE",file,flush=True)
w.close();app.processEvents()
print("V87_REAL_TRACE_GUI_QA_ALL_PASS",flush=True)
