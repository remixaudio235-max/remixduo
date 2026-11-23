"""Top-3 route coverage including inverted polarity and trace-1 delay."""
from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from overlay_v7 import App
from trf_core import Candidate, read_trf, compute_sum
from positive_delay_route_v87 import route_candidate
from signal_tools_gui_v813 import ToolHub

app=QApplication([])
e=App(False);e.timer.stop()
hub=ToolHub(e);hub.timer.stop()
src=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
e.current_traces=tuple(read_trf(src/f) for f in ("SUb.trf","FULL.trf"))
e.current_pair=tuple(str(t.path) for t in e.current_traces)
e.recalc()
samples=[
    Candidate(7.3,False,-0.05,100),   # delay T2, NORMAL
    Candidate(-6.2,True,-0.15,100),   # delay T1, INVERT
    Candidate(-1.7,False,-0.25,100),  # delay T1, NORMAL
]
e.last_solve=samples
e._candidate_scope=e._candidate_key()
e._display_candidates()
for i,c in enumerate(samples):
    r=route_candidate(c)
    QTest.mouseClick(e.candidates[i],Qt.MouseButton.LeftButton)
    app.processEvents()
    assert e.active_candidate_index==i
    assert e._reference_index()==r.reference_index
    assert e.invert.isChecked()==r.invert_target
    assert abs(e.delay.value()-r.delay_ms)<.011
    assert e.candidates[i].isChecked()
    assert sum(b.isChecked() for b in e.candidates)==1
    label=e.trace_compact_result[r.delay_target_index].text()
    assert f"Delay: {r.delay_ms:.2f} ms" in label
    assert ("Đảo pha" in label)==r.invert_target
    signed=compute_sum(*e.current_traces,c.delay_ms,c.invert_trace2,mag_oct=float(e.mag_smooth.currentData() or 0),phase_oct=float(e.phase_smooth.currentData() or 0))
    real=e.current_sum
    mask=np.isfinite(signed.mag_db)&np.isfinite(real.mag_db)
    assert np.max(np.abs(signed.mag_db[mask]-real.mag_db[mask]))<1e-6
    print("ROUTE",i+1,"TRACE",r.delay_trace,
          "DELAY",r.delay_ms,"INV",r.invert_target,"MAG_PARITY_PASS",flush=True)
hub.close()
print("V817_POSITIVE_TARGET_AND_POLARITY_ALL_PASS",flush=True)
