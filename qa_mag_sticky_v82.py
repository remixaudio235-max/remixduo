from pathlib import Path
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from trf_core import read_trf
folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(folder/n) for n in ("4,8 ms delay-1.trf","0 delay-1.trf"))
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
gui.current_pair=(str(a.path),str(b.path))
gui.current_traces=(a,b)
gui.recalc()
key_before=gui._mag_offset_key
assert key_before is not None
# Force a visible preview offset, mimicking the default -60dB stored trace
# preview, to ensure recomputation never silently resets it.
gui.graph_mag.display_offset_db=-62.7
gui.mag_min.setValue(-120.3)
gui.mag_max.setValue(-84.3)
assert gui.graph_mag.display_offset_db==-62.7
gui.align()
assert gui.graph_mag.display_offset_db==-62.7
assert gui._mag_offset_key==key_before
print("MAG_PREVIEW_OFFSET_STICKY_AFTER_AXIS_AND_ALIGN_PASS",flush=True)
gui.mag_fit.setChecked(False)
assert gui.graph_mag.display_offset_db==0.
print("MAG_PREVIEW_TOGGLE_OFF_RESETS_OFFSET_PASS",flush=True)
gui.mag_fit.setChecked(True)
assert gui._mag_offset_key!=None
print("MAG_PREVIEW_TOGGLE_ON_REEVALUATES_PASS",flush=True)
gui.close();app.processEvents()
print("V82_MAG_STICKY_QA_PASS",flush=True)
