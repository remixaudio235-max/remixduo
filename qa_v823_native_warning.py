"""Native Smaart 108/108 QA for V8.23 multiple-enabled warning.
The scanner is read-only except temporary Data Bar scroll restored.
"""
import time
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from live_sync_v7 import LiveDataBarV7
from signal_tools_gui_v813 import ToolHub
from win_databar_v7 import locate_smaart
app=QApplication([])
engine=App(False)
engine.timer.stop()
hub=ToolHub(engine)
hub.timer.stop()
hub.native_eq.timer.stop()
target=locate_smaart()
assert target
reader=LiveDataBarV7(Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data")
r=reader.poll(target.hwnd)
engine.observer=reader
engine.found(r)
app.processEvents()
count=sum(x=="on" for x in reader.states.values())
print("VERIFIED_NATIVE_TICKS",r.verified,r.rows,"ON",count,
      "TRACE",[(i,reader.order[i].name) for i,v in reader.states.items() if v=="on"],flush=True)
assert r.verified==r.rows==108
assert count>=2
if count!=2:
    assert r.pair is None
    assert engine.controller.last_pair is None
    assert engine.selection_warning.isVisible() or engine.selection_warning.isHidden()==False
    assert f"Đang bật {count} Trace" in engine.selection_warning.text()
    assert not any(w.isVisible() for w in engine.trace_name_labels)
    assert not engine.graph_mag.isVisible() and not engine.graph_phase.isVisible()
    hub.dock.apply_rect((1712,484,205,446))
    hub.select("phase")
    hub.show()
    hub.dock.show()
    app.processEvents()
    assert hub.dock.grab().save(str(Path(__file__).parent/"V823_MULTI_TICK_WARNING_QA.png"))
    print("MULTI_TICK_NO_ARBITRARY_PAIR_WARNING_PASS",flush=True)
else:
    assert r.pair and engine.controller.last_pair
    print("EXACT_TWO_TICKS_AUTO_BIND_PASS",flush=True)
hub.close()
app.processEvents()
print("V823_NATIVE_DATABAR_UI_ALL_PASS",flush=True)
