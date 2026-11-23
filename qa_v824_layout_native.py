"""V8.24 real Windows Qt layout / viewport and Hide/Live regression.

This does not touch Smaart UI, soundcard, generator or DSP.
"""
from pathlib import Path
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from live_sync_v7 import SyncResult
from time import perf_counter,sleep
import win32gui
root=Path(__file__).resolve().parent
app=QApplication([])
e=App(False);e.timer.stop()
hub=ToolHub(e);hub.timer.stop();hub.native_eq.timer.stop()
data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
names=tuple(str(data/n) for n in ("4,8 ms delay-1.trf","0 delay-1.trf"))
for _ in range(3):
    e.found(SyncResult(names,"Verified 108/108 rows, active 2",
                       108,108,True,perf_counter(),names))
    app.processEvents()
assert e._selection_verified
hub.select("phase")
hub.dock.apply_rect((1490,437,205,313))
hub.show();hub.dock.show();app.processEvents()
assert e.candidate_card.isVisible()
assert len(e.candidates)==3
viewport=hub.dock.scroll.viewport()
last=e.candidates[2]
bottom=last.mapTo(viewport,QPoint(0,last.height())).y()
print("LAYOUT last_candidate_bottom",bottom,"viewport_height",viewport.height(),
      "dock_height",hub.dock.height(),"stack_height",hub.dock.stack.height(),flush=True)
assert bottom <= viewport.height()-2,("Top3 clipped",bottom,viewport.height())
assert hub.dock.scroll.verticalScrollBar().value()==0
assert hub.dock.grab().save(str(root/"V824_NATIVE_PANEL_ALL_TOP3.png"))
print("COMPACT_TOP3_ALL_VISIBLE_NATIVE_PASS",flush=True)
hub.select("eq");app.processEvents()
assert not e.graph_phase.isVisible()
hub.select("fir");app.processEvents()
assert not e.graph_phase.isVisible() and not e.graph_mag.isVisible()
hub.select("phase");app.processEvents()
hub.hide_workspace();app.processEvents()
assert not hub.dock.isVisible() and not e.graph_phase.isVisible()
hub._last_host_rect=(0,0,1920,1000)
hub._anchors=None
hub.select("phase")
app.processEvents()
assert hub.dock.isVisible()
hub.dock.live_btn.click();app.processEvents()
assert not hub.dock.isVisible() and not e.graph_phase.isVisible()
print("HIDE_LIVE_EQ_FIR_EXCLUSIVITY_PASS",flush=True)
hub.close()
app.processEvents()
print("V824_NATIVE_QT_LAYOUT_PASS",flush=True)
