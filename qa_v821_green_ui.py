from pathlib import Path
from PyQt6.QtWidgets import QApplication,QLabel
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
app=QApplication([])
engine=App(False);engine.timer.stop()
hub=ToolHub(engine);hub.timer.stop()
hub.dock.apply_rect((1478,400,205,385))
hub.select('phase')
hub.show();hub.dock.show();app.processEvents()
root=engine.layout()
button_card=engine.solve.parentWidget()
trace_label=next(x for x in engine.findChildren(QLabel) if x.objectName()=='sectionTitle' and x.text().startswith('TRACE'))
trace_card=trace_label.parentWidget()
print('CARD_ORDER',root.indexOf(button_card),root.indexOf(trace_card))
assert root.indexOf(button_card)<root.indexOf(trace_card)
assert engine.solve.text()=='AUTO PHASE'
assert '#39FF14' in engine.styleSheet()
assert '#39FF14' in hub.buttons['phase'].styleSheet()
assert '#71FF55' in hub.dock.heading.styleSheet()
assert hub.active=='phase'
assert engine.solve.isVisible()
assert hub.dock.grab().save('V821_AUTO_PHASE_GREEN_PANEL.png')
assert hub.grab().save('V821_TOOLBAR_GREEN.png')
for mode in ('eq','fir','phase'):
    hub.select(mode);app.processEvents();assert hub.active==mode
hub.close();app.processEvents()
print('V821_GUI_GREEN_POSITION_QA_PASS')