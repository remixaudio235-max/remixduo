"""Offscreen Qt mock: no windows shown, no network or real license changes."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import threading
import time
from types import SimpleNamespace


def test_slow_activation_keeps_qt_event_loop_responsive(monkeypatch):
    from PyQt6.QtCore import QEventLoop,QTimer
    from PyQt6.QtWidgets import QApplication,QDialog,QLineEdit,QPushButton,QLabel
    import remix_duo_license_v874 as gate
    import remix_duo_online_license_v878 as online
    app=QApplication.instance() or QApplication([])
    main_thread=threading.get_ident()
    calls=[]
    def slow_network(*args,**kwargs):
        calls.append(threading.get_ident())
        time.sleep(.15)
        return SimpleNamespace(valid=False,message='TEST: request finished',status='TEST')
    monkeypatch.setattr(online,'activate_online_and_save',slow_network)
    monkeypatch.setattr(gate,'machine_code',lambda:'DUO2-'+'A'*32)
    monkeypatch.setattr(gate,'load_installed_license',lambda **_:SimpleNamespace(valid=False))
    def mock_exec(dialog):
        field=next(w for w in dialog.findChildren(QLineEdit) if not w.isReadOnly())
        field.setText('TEST-ONLY')
        activate=next(w for w in dialog.findChildren(QPushButton) if w.text()=='Kích hoạt online')
        activate.click()
        assert dialog.busy and not activate.isEnabled()
        beats=[]
        loop=QEventLoop()
        timer=QTimer()
        timer.timeout.connect(lambda:beats.append(1))
        timer.start(10)
        QTimer.singleShot(350,loop.quit)
        loop.exec()
        timer.stop()
        assert len(beats)>=5, 'Slow activation blocked the Qt event loop'
        assert calls and calls[0]!=main_thread
        assert not dialog.busy and activate.isEnabled()
        assert any(w.text()=='TEST: request finished' for w in dialog.findChildren(QLabel))
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(QDialog,'exec',mock_exec)
    assert gate.activation_gate() is False


def test_toast_reuses_label_and_restarts_readable_timeout():
    from PyQt6.QtWidgets import QApplication,QDialog
    from signal_tools_gui_v813 import show_notice
    app=QApplication.instance() or QApplication([])
    owner=QDialog();owner.resize(446,400)
    show_notice(owner,'Chưa xác minh tick — hãy giữ hàng Trace trong vùng nhìn thấy.')
    label=owner._remix_notice
    assert label.wordWrap() and not label.isHidden()
    assert owner._remix_notice_timer.isActive()
    assert owner._remix_notice_timer.interval()==5000
    show_notice(owner,'Auto EQ cần đúng 1 Trace đã xác minh.')
    assert owner._remix_notice is label
    assert label.text()=='Auto EQ cần đúng 1 Trace đã xác minh.'
    assert label.objectName()=='remixToast'
    assert label.property('toastTone')=='warning'
    owner._remix_notice_timer.stop()
