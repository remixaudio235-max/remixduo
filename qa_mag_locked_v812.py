from pathlib import Path
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from trf_core import read_trf
data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(data/n) for n in ("4,8 ms delay-1.trf","0 delay-1.trf"))
app=QApplication([])
w=App(demo=False);w.timer.stop()
w.current_pair=(str(a.path),str(b.path))
w.current_traces=(a,b);w.recalc()
w.graph_mag.display_offset_db=-62.7
key=w._mag_offset_key
w.mag_min.setValue(-120.3);w.mag_max.setValue(-84.3)
assert w.graph_mag.display_offset_db==-62.7
w.align()
assert w.graph_mag.display_offset_db==-62.7 and w._mag_offset_key==key
# V8.11+ intentionally forbids disabling AUTO-FIT. Old V8.2
# toggle-off test is obsolete; new contract keeps feature permanently ON.
w.mag_fit.setChecked(False)
assert w.mag_fit.isChecked()
assert w.graph_mag.display_offset_db==-62.7
w.mag.setChecked(False);w.phase.setChecked(False)
w.refresh_visibility()
assert w.mag.isChecked() and w.phase.isChecked()
print("V812_MAG_STICKY_AND_ALWAYS_ON_QA_PASS")
w.close();app.processEvents()
