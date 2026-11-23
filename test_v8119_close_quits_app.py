"""V8.119: "Đóng RemiX Duo" must end the process.

Live 2026-11-11: after the menu close the overlay process stayed alive and
its SUM / LF-HF windows stayed painted over Chrome. All Duo windows are
Qt.Tool windows, which never trigger quit-on-last-window-closed.
"""
import os,time
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication


def test_menu_close_quits_event_loop_and_hides_overlays():
    import overlay_v7 as gui
    from signal_tools_gui_v813 import ToolHub
    app=QApplication.instance() or QApplication([])
    e=gui.App(False)
    hub=ToolHub(e,"RemiX Duo","")
    QTimer.singleShot(300,hub._menu.actions()[-1].trigger)   # "Đóng RemiX Duo"
    guard={"timed_out":False}
    def timeout():
        guard["timed_out"]=True;app.quit()
    QTimer.singleShot(5000,timeout)
    t0=time.monotonic();app.exec()
    assert not guard["timed_out"], "event loop kept running after Đóng RemiX Duo"
    assert time.monotonic()-t0<3
    assert not e.graph_mag.isVisible() and not e.graph_phase.isVisible()
    assert not hub.isVisible() and not hub.dock.isVisible()


def test_peq_drag_module_has_os_imported():
    import signal_tools_gui_v813 as tools
    assert hasattr(tools,"os")   # PEQ drag reject path used os.environ (NameError)
