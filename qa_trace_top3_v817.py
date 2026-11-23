"""V8.17 Top 3 selectable preview + large Trace readouts, no Smaart writes."""
from pathlib import Path
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from trf_core import read_trf, compute_sum
from positive_delay_route_v87 import route_candidate
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub

root=Path(__file__).resolve().parent
app=QApplication([])
engine=App(demo=False)
engine.timer.stop()
hub=ToolHub(engine)
hub.timer.stop()
engine.current_traces=tuple(read_trf(
    Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"/n
) for n in ("4,8 ms delay-1.trf","0 delay-1.trf"))
engine.current_pair=tuple(str(t.path) for t in engine.current_traces)
engine.recalc()
assert len(engine.candidates)==3
assert all(not w.isEnabled() for w in engine.candidates)
assert "font:bold 12px" in engine.trace_name_labels[0].styleSheet()
engine.align()
assert engine.last_solve is not None
assert len(engine.last_solve)>=3
assert engine.active_candidate_index==0
print("ALIGN_TOP3",[(w.text(),w.isEnabled()) for w in engine.candidates],flush=True)
assert all(w.isEnabled() for w in engine.candidates)
assert all("Delay:" in w.text() for w in engine.candidates)
assert all("Trace " in w.text() for w in engine.candidates)
assert all(("Đảo pha" in w.text() or "Không đảo" in w.text()) for w in engine.candidates)
assert "dB" not in " ".join(w.text() for w in engine.candidates)
assert "Delay:" in engine.trace_compact_result[0].text()
assert "Delay:" in engine.trace_compact_result[1].text()
assert all("Đảo" in w.text() or "đảo" in w.text() for w in engine.trace_compact_result)
assert "font:bold 12px" in engine.trace_compact_result[0].styleSheet()
assert "font:bold 12px" in engine.trace_compact_result[1].styleSheet()

for idx in (2,1,0,2):
    expected=route_candidate(engine.last_solve[idx])
    QTest.mouseClick(engine.candidates[idx],Qt.MouseButton.LeftButton)
    app.processEvents()
    assert engine.active_candidate_index==idx,(idx,engine.active_candidate_index)
    assert engine.candidates[idx].isChecked()
    assert sum(c.isChecked() for c in engine.candidates)==1
    assert engine._reference_index()==expected.reference_index
    assert abs(engine.delay.value()-expected.delay_ms)<.011
    assert engine.invert.isChecked()==expected.invert_target
    assert engine.current_sum is not None
    orig=compute_sum(*engine._ordered_traces(),
                     delay_ms=engine.delay.value(),
                     invert_trace2=engine.invert.isChecked(),
                     coh_gate=.60,
                     mag_oct=float(engine.mag_smooth.currentData() or 0),
                     phase_oct=float(engine.phase_smooth.currentData() or 0))
    assert np.allclose(engine.current_sum.mag_db,orig.mag_db,atol=1e-8,equal_nan=True)
    target=expected.delay_target_index
    assert f"Delay: {expected.delay_ms:.2f} ms" in engine.trace_compact_result[target].text()
    if expected.invert_target:
        assert "Đảo pha" in engine.trace_compact_result[target].text()
    else:
        assert "Không đảo" in engine.trace_compact_result[target].text()
    print("PREVIEW_SELECTED",idx+1,"TARGET",expected.delay_trace,
          "DELAY",expected.delay_ms,"INVERT",expected.invert_target,flush=True)

# Apply does not mutate original traces or system DSP / Smaart.
assert engine.current_pair == tuple(str(t.path) for t in engine.current_traces)
assert all(w.isEnabled() for w in engine.candidates)
hub._anchors=None
hub.select("phase")
app.processEvents()
assert hub.dock.heading.text()=="AUTO PHASE"
# Force a large preview window for legibility capture in QA.
hub.dock.setFixedHeight(385)
hub.dock.show()
hub.dock.scroll.verticalScrollBar().setValue(0)
app.processEvents()
assert hub.dock.grab().save(str(root/"V817_TRACE_TOP3_START.png"))
hub.dock.scroll.verticalScrollBar().setValue(hub.dock.scroll.verticalScrollBar().maximum())
app.processEvents()
assert hub.dock.grab().save(str(root/"V817_TRACE_TOP3_END.png"))
# Changing ROI makes all formerly computed choices invalid.
engine.hf.setValue(engine.hf.value()+31)
app.processEvents()
assert engine.last_solve is None
assert engine.active_candidate_index is None
assert all(not c.isEnabled() for c in engine.candidates)
assert not engine.select_candidate(0)
print("ROI_STALE_RESULTS_BLOCKED_PASS",flush=True)
# A new valid Auto Align provides new top choices.
engine.align()
assert engine.active_candidate_index==0
assert engine._candidate_scope is not None
engine.ref_choice.setCurrentIndex(1-engine._reference_index())
assert engine.last_solve is None
assert all(not c.isEnabled() for c in engine.candidates)
print("MANUAL_REF_INVALIDATES_TOP3_PASS",flush=True)
# Trace pair change clears all results; cannot operate on stale trace.
engine.on_selection(None)
assert not any(c.isEnabled() for c in engine.candidates)
assert engine.last_solve is None
print("PAIR_CHANGE_CLEARS_TOP3_PASS",flush=True)
hub.close()
app.processEvents()
print("V817_TRACE_TOP3_SELECTION_ALL_PASS",flush=True)
