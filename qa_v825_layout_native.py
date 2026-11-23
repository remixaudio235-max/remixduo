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
hub.dock.apply_rect((1490,437,205,446))
hub.show();hub.dock.show();app.processEvents()
assert e.candidate_card.isVisible()
assert len(e.candidates)==3
assert hub.dock.height()==446
assert hub.dock.stack.height()==400
assert e.solve.height()==26
assert e.solve.parentWidget().height()==36
assert e.solve.height()==26
print("ACTION_CARD_HEIGHT",e.solve.parentWidget().height(),"BUTTON_HEIGHT",e.solve.height(),flush=True)
assert e.trace_name_labels[0].minimumHeight()==22
print("TOP3_HEIGHT",e.candidates[0].height(),"CONFIG",e.candidates[0].minimumHeight(),flush=True)
viewport=hub.dock.scroll.viewport()
last=e.candidates[2]
bottom=last.mapTo(viewport,QPoint(0,last.height())).y()
print("LAYOUT last_candidate_bottom",bottom,"viewport_height",viewport.height(),
      "dock_height",hub.dock.height(),"stack_height",hub.dock.stack.height(),flush=True)
assert bottom <= viewport.height()-2,("Top3 clipped",bottom,viewport.height())
assert hub.dock.scroll.verticalScrollBar().value()==0
assert hub.dock.grab().save(str(root/"V825_FULL_DIALOG_SMALL_BUTTON.png"))
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
print("V825_BUTTON_ONLY_FULL_DIALOG_QT_PASS",flush=True)
