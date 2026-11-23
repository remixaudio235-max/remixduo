from pathlib import Path
from PyQt6.QtWidgets import QApplication,QLabel,QWidget
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from trf_core import read_trf
root=Path(__file__).resolve().parent
app=QApplication([])
engine=App(False)
engine.timer.stop()
hub=ToolHub(engine)
hub.timer.stop()
hub._anchors=None
hub.dock.select("phase")
hub.dock.apply_rect((1500,400,205,385))
hub.dock.show()
hub.show()
app.processEvents()
labels=[x for x in engine.findChildren(QLabel) if x.objectName()=="sectionTitle" and x.isVisible()]
texts=[x.text().strip() for x in labels]
print("VISIBLE_SECTION_TITLES",texts,flush=True)
assert len(texts)==2,texts
assert texts[0].startswith("TRACE"),texts
assert texts[1].startswith("TOP 3"),texts
assert all(not x.startswith(("01 ","02 ","03 ")) for x in texts)
assert engine.solve.text()=="AUTO PHASE"
assert engine.solve.isVisible()
assert len(engine.candidates)==3
assert all(x.isVisible() for x in engine.candidates)
assert hub.active=="phase"
assert hub.dock.heading.text()=="AUTO PHASE"
assert hub.dock.grab().save(str(root/"V820_CLEAN_PANEL_QA.png"))
print("V820_UI_SECTION_REMOVAL_PASS",flush=True)
paths=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(paths/n) for n in ("SUb.trf","FULL.trf"))
engine.current_pair=(str(a.path),str(b.path))
engine.current_traces=(a,b)
engine.recalc()
engine.align()
assert abs(engine.delay.value()-13.2)<.2,engine.delay.value()
print("V820_AUTO_PHASE_DELAY_UNCHANGED_PASS",engine.delay.value(),flush=True)
hub.select("eq")
assert hub.active=="eq"
hub.select("fir")
assert hub.active=="fir"
hub.select("phase")
assert hub.active=="phase"
print("V820_NAVIGATION_PASS",flush=True)
hub.close()
app.processEvents()
print("V820_GUI_QA_ALL_PASS",flush=True)
