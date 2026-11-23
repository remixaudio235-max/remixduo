from pathlib import Path
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication
from trf_core import read_trf
from overlay_v7 import App
app=QApplication([])
gui=App(demo=False)
gui.timer.stop()
folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(folder/name) for name in ("4,8 ms delay-1.trf","0 delay-1.trf"))
gui.current_traces=(a,b)
gui.pair_label.setText("TRACE 1: "+a.path.stem+"\nTRACE 2: "+b.path.stem)
gui.hf.setValue(527.2)
gui.delay.setValue(4.8)
gui.recalc()
for label,idx in (("V76_PANEL_REF1_QA.png",0),("V76_PANEL_REF2_QA.png",1)):
    gui.ref_choice.setCurrentIndex(idx)
    gui.align()
    img=QImage(gui.width(),gui.height(),QImage.Format.Format_ARGB32)
    img.fill(0)
    gui.render(img)
    assert img.save(label)
    print("SNAPSHOT",label,gui.ref_choice.currentText(),
          gui.delay.value(),gui.phase_match_label.text(),
          gui.sum_ref_label.text())
gui.close()
app.processEvents()
