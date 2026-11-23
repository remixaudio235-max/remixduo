"""V8.90: QFileDialog must not invoke native Windows shell picker from Qt.Tool."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication,QFileDialog
from test_v845_fir_one_trace import init,wait_fir


def test_actual_qt_export_dialog_completes_txt_and_wav(tmp_path):
    app,obs,engine,hub,fir=init()
    try:
        # Export-picker parity is independent of the default PHA setting.
        fir.fir_mag_button.click()
        fir.compute()
        wait_fir(app,fir)
        assert fir.result is not None and fir._proof_current()
        for fmt in ("txt","wav"):
            target=tmp_path/("fir_qa."+fmt)
            found=[]
            def accept_dialog():
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget,QFileDialog) and widget.isVisible():
                        assert widget.testOption(QFileDialog.Option.DontUseNativeDialog)
                        widget.setDirectory(str(tmp_path))
                        widget.selectFile(target.name)
                        found.append(widget.windowTitle())
                        widget.accept()
                        return
                QTimer.singleShot(50,accept_dialog)
            QTimer.singleShot(100,accept_dialog)
            fir._export(fmt)
            assert found,(fmt,"Qt dialog not shown")
            exported=list(tmp_path.glob("*."+fmt))
            assert len(exported)==1 and exported[0].stat().st_size>100,exported
    finally:
        hub.close()
        app.processEvents()


def test_all_fir_save_commands_disable_windows_native_picker(monkeypatch,tmp_path):
    app,obs,engine,hub,fir=init()
    calls=[]
    try:
        fir.fir_mag_button.click()
        fir.compute();wait_fir(app,fir)
        assert fir._proof_current()
        def file_picker(*args,**kwargs):
            assert kwargs.get("options")==QFileDialog.Option.DontUseNativeDialog
            calls.append(str(args[1]))
            return (str(tmp_path/("qa_"+str(len(calls))+".txt")),"")
        monkeypatch.setattr(QFileDialog,"getSaveFileName",file_picker)
        fir.save_txt()
        fir.save_wav()
        assert len(calls)==2
    finally:
        hub.close()
        app.processEvents()
