"""V8.118: a stalled Qt GUI thread leaves a stack dump in the overlay log."""
import os,time
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import faulthandler
from PyQt6.QtWidgets import QApplication
from gui_watchdog_v8118 import install,log_path


def test_stall_dumps_all_thread_stacks(tmp_path):
    app=QApplication.instance() or QApplication([])
    log,timer=install(app,stall_s=.3,directory=tmp_path,redirect=False)
    try:
        app.processEvents()
        time.sleep(.8)                      # GUI thread blocked, no heartbeat
        text=log_path(tmp_path).read_text(encoding="utf-8")
        assert "RemiX Duo overlay start" in text
        assert "Thread" in text and "test_stall_dumps_all_thread_stacks" in text
    finally:
        timer.stop();faulthandler.cancel_dump_traceback_later()
        faulthandler.disable();log.close()


def test_heartbeat_prevents_dump_while_responsive(tmp_path):
    app=QApplication.instance() or QApplication([])
    log,timer=install(app,stall_s=1.5,directory=tmp_path,redirect=False)
    try:
        end=time.monotonic()+2.5
        while time.monotonic()<end:
            app.processEvents();time.sleep(.02)
        assert "Thread" not in log_path(tmp_path).read_text(encoding="utf-8")
    finally:
        timer.stop();faulthandler.cancel_dump_traceback_later()
        faulthandler.disable();log.close()
