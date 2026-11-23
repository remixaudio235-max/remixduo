import threading
import time
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication

from roi_markers_v73 import ROILineGrip, ROIMarker
from uia_serial_v8152 import serialized_uia, uia_serial_section


def test_all_uia_workers_are_process_serialized():
    active = 0
    peak = 0
    state_lock = threading.Lock()
    release = threading.Event()

    @serialized_uia
    def reader():
        nonlocal active, peak
        with state_lock:
            active += 1
            peak = max(peak, active)
        release.wait(1.0)
        with state_lock:
            active -= 1

    workers = [threading.Thread(target=reader) for _ in range(4)]
    for worker in workers:
        worker.start()
    time.sleep(0.05)
    release.set()
    for worker in workers:
        worker.join(2.0)
    assert peak == 1
    assert all(not worker.is_alive() for worker in workers)


def test_uia_guard_is_reentrant_for_nested_scan_calls():
    @serialized_uia
    def nested():
        with uia_serial_section():
            return "ok"

    assert nested() == "ok"


def test_every_smaart_uia_entrypoint_uses_the_shared_guard():
    from dock_geometry_v815 import read_smaart_anchors
    from full_scan_v7 import full_scan
    from live_sync_v7 import LiveDataBarV7
    from plot_geometry_v7 import locate_plots
    from smaart_live_smooth_v8115 import read_live_smoothing
    from smaart_mag_geometry_readonly import locate_plots as locate_mag_plots
    from win_databar_v7 import UIADataBarObserver

    readers = (
        read_smaart_anchors,
        full_scan,
        LiveDataBarV7.poll,
        locate_plots,
        read_live_smoothing,
        locate_mag_plots,
        UIADataBarObserver.poll,
    )
    assert all(hasattr(reader, "__wrapped__") for reader in readers)


def test_stale_mouse_grab_cannot_emit_phantom_roi_drag():
    app = QApplication.instance() or QApplication([])
    for widget_type in (ROIMarker, ROILineGrip):
        calls = []
        widget = widget_type("LF", lambda *args: calls.append(args))
        widget.dragging = True
        event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(4, 4),
            QPointF(4, 4),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mouseMoveEvent(event)
        assert not widget.dragging
        assert calls == []
        widget.close()
    app.processEvents()


def test_autophase_completion_never_touches_qt_from_worker_callback():
    source = (Path(__file__).parent / "overlay_v7.py").read_text(encoding="utf-8")
    solve_start = source.index("def align(self)")
    finish_start = source.index("def _finish_alignment", solve_start)
    solve_body = source[solve_start:finish_start]
    assert "add_done_callback" not in solve_body
    assert "self._align_completion_timer.start()" in solve_body
    assert "def _poll_alignment_completion" in solve_body
    assert "self._finish_alignment(ticket,context,future)" in solve_body


def test_cython_autophase_slot_consumes_qpushbutton_checked_argument():
    source = (Path(__file__).parent / "overlay_v7.py").read_text(encoding="utf-8")
    assert "self.solve.clicked.connect(self._on_align_clicked)" in source
    assert "def _on_align_clicked(self,checked=False):" in source
    assert "self.solve.clicked.connect(self.align)" not in source


def test_gui_thread_requests_sta_before_any_uia_import():
    source = (Path(__file__).parent / "overlay_v7.py").read_text(encoding="utf-8")
    sta = source.index("sys.coinit_flags = 2")
    assert sta < source.index("from win_databar_v7 import")
    assert sta < source.index("from live_sync_v7 import")


def test_qt_callback_exception_is_logged_without_fatal_app_exit(tmp_path):
    log = tmp_path / "qt-callback.log"
    script = f'''\
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QPushButton
from gui_watchdog_v8118 import install_exception_boundary
stream = open({str(log)!r}, "w", encoding="utf-8", buffering=1)
install_exception_boundary(stream)
app = QApplication([])
button = QPushButton()
button.clicked.connect(lambda: 1 / 0)
button.click()
print("SURVIVED")
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "SURVIVED" in result.stdout
    report = log.read_text(encoding="utf-8")
    assert "V8154_QT_CALLBACK_EXCEPTION" in report
    assert "ZeroDivisionError" in report
