import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
app=QApplication.instance() or QApplication([])
engine=App(demo=True);engine.timer.stop()
hub=ToolHub(engine);hub.timer.stop();hub.follow_timer.stop();hub.native_eq.timer.stop()
# V8.107: no LAN page exists, so ToolHub construction/close never opens a port.
assert not any(type(w).__name__=='RemoteControlPage' for w in hub.dock.stack.children())
hub.close()
print('PASS: ToolHub lifecycle without LAN remote page')
