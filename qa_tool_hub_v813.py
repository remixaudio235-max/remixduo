"""V8.13 tool-window router QT QA. No hardware, no Smaart writes."""
from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from trf_core import read_trf

root=Path(__file__).resolve().parent
app=QApplication([])
engine=App(demo=False)
engine.timer.stop()
hub=ToolHub(engine)
hub.timer.stop()
app.processEvents()
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(p/name) for name in ("SUb.trf","FULL.trf"))
engine.current_pair=(str(a.path),str(b.path))
engine.current_traces=(a,b)
engine.recalc()
engine.align()
assert len(hub.buttons)==3
assert hub.active=="phase"
assert engine.isVisible() and not hub.eq.isVisible() and not hub.fir.isVisible()
assert hub.grab().save(str(root/"V813_HUB.png"))
assert engine.grab().save(str(root/"V813_AUTO_PHASE.png"))
print("AUTO_PHASE_WINDOW_PASS",flush=True)
hub.select("eq");app.processEvents()
assert hub.active=="eq" and hub.eq.isVisible()
assert not engine.isVisible() and not hub.fir.isVisible()
hub.eq.source.setCurrentIndex(0)
hub.eq.compute()
assert hub.eq.result is not None
assert hub.eq.result.bins>=20
assert "PEQ" in hub.eq.summary.text()
assert hub.eq.grab().save(str(root/"V813_AUTO_EQ.png"))
print("AUTO_EQ_WINDOW_PASS",hub.eq.summary.text(),flush=True)
hub.select("fir");app.processEvents()
assert hub.active=="fir" and hub.fir.isVisible()
assert not engine.isVisible() and not hub.eq.isVisible()
hub.fir.source.setCurrentIndex(2)
hub.fir.taps.setCurrentIndex(1)
hub.fir.compute()
assert hub.fir.result is not None
assert len(hub.fir.result.taps)==1024
assert hub.fir.grab().save(str(root/"V813_FIR.png"))
print("FIR_WINDOW_PASS",hub.fir.summary.text(),flush=True)
hub.select("phase");app.processEvents()
assert hub.active=="phase"
assert engine.isVisible() and not hub.fir.isVisible() and not hub.eq.isVisible()
assert abs(engine.delay.value()-13.2)<.15
print("REENTER_PHASE_PRESERVES_AUTO_ALIGN_PASS",flush=True)
# Sync source switch must be explicit; no stale EQ preview for another pair.
a2,b2=(read_trf(p/name) for name in ("4,8 ms delay-1.trf","0 delay-1.trf"))
engine.current_traces=(a2,b2);engine.current_pair=(str(a2.path),str(b2.path))
hub.select("eq");app.processEvents()
assert hub.eq.result is None
assert "4,8 ms" in hub.eq.source.itemText(0)
hub.eq.compute();assert hub.eq.result is not None
print("TRACE_CHANGE_REFRESHES_EQ_INPUTS_PASS",flush=True)
# Only the active dialog may appear; test all modes repeatedly.
for mode in ("fir","eq","phase","fir","phase"):
 hub.select(mode);app.processEvents()
 shown=[engine.isVisible(),hub.eq.isVisible(),hub.fir.isVisible()]
 assert shown.count(True)==1,(mode,shown)
 print("SINGLE_DIALOG",mode,shown,flush=True)
hub.close();app.processEvents()
print("V813_TOOL_HUB_GUI_ALL_PASS",flush=True)
