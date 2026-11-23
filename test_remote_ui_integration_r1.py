import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
app=QApplication.instance() or QApplication([])
engine=App(demo=True);engine.timer.stop()
hub=ToolHub(engine);hub.timer.stop();hub.follow_timer.stop();hub.native_eq.timer.stop()
try:
    # V8.107: the "Dieu khien" LAN tool was removed from the Duo toolbar.
    assert set(hub.buttons)=={'phase','eq','fir'}
    assert 'remote' not in hub.dock.pages
    assert not hasattr(hub.dock,'remote')
    labels=[a.text() for a in hub.menu_button.menu().actions()]
    assert labels==['Auto Phase','Auto EQ','Auto FIR'],labels
    for mode in ('phase','eq','fir','phase'):
        hub.select(mode)
        assert hub.active==mode
        assert hub.dock.stack.currentWidget() is hub.dock.pages[mode]
    for mode in ('compact','mini','full'):
        hub._set_toolbar_mode(mode)
        assert len([b for b in hub.buttons.values() if not b.isHidden()])==3
    print('PASS: three buttons, no LAN page/server, page transitions intact')
finally:
    hub.close();app.processEvents()
