import os
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
app=QApplication([])
engine=App(demo=True)
engine.timer.stop()
hub=ToolHub(engine)
hub.timer.stop()
hub.follow_timer.stop()
hub.native_eq.timer.stop()
hub.select('remote')
hub.setWindowTitle('RemiX Duo - QR LAN QA ONLY')
hub.show()
hub.dock.show()
hub.pages['remote'].start()
print('QA_GUI_STARTED',flush=True)
print('QA_URL',hub.pages['remote'].server.url,flush=True)
def cleanup():
    hub.close()
    app.quit()
app.aboutToQuit.connect(lambda:hub.pages['remote'].stop())
raise SystemExit(app.exec())
