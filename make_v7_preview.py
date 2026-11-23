"""Capture GUI QA preview without depending on another desktop app's focus."""
from pathlib import Path
import time
from PIL import Image,ImageGrab
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from overlay_v7 import App
P=Path(__file__).resolve().parent
qt=QApplication([])
ui=App(demo=True)
limit=time.time()+3
while time.time()<limit and not ui.current_sum:
    qt.processEvents();time.sleep(.02)
assert ui.current_sum
ui.host.show()
ui.host.grab().save(str(P/"_v7_host.png"))
ui.graph_mag.grab().save(str(P/"_v7_mag.png"))
ui.graph_phase.grab().save(str(P/"_v7_phase.png"))
ui.grab().save(str(P/"_v7_panel.png"))
background=Image.open(P/"_v7_host.png").convert("RGBA")
boxes=ui.host.plot_boxes()
for graph,name,file in ((ui.graph_mag,"MAGNITUDE","_v7_mag.png"),
                        (ui.graph_phase,"PHASE","_v7_phase.png")):
    overlay=Image.open(P/file).convert("RGBA")
    x,y,w,h=boxes[name]
    background.alpha_composite(overlay,(x,y))
panel=Image.open(P/"_v7_panel.png").convert("RGBA")
background.alpha_composite(panel,(ui.host.width()-panel.width-5,43))
out=P/"V7_QA_COMPOSITE.png"
background.save(out)
print("V7_QA_PREVIEW_CREATED",out,"size",background.size)
ui.close()
qt.quit()
