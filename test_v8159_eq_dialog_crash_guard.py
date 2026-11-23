# -*- coding: utf-8 -*-
"""V8.159 P0 regression: EQ save dialogs must not enter Windows native COM dialogs."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QFileDialog
from autoeq_export_dialog_v08 import EQRow, EQExportSnapshot, EQExportDialog


@pytest.mark.parametrize("format_name", ["txt", "png"])
def test_eq_save_uses_qt_dialog_and_writes_expected_file(tmp_path, monkeypatch, format_name):
    app = QApplication.instance() or QApplication([])
    snap = EQExportSnapshot(
        source="verified-trace", target="Flat", fs=48000,
        before_wrms=4.1, after_wrms=1.8,
        rows=(EQRow(1, 200.0, -2.5, 4.0), EQRow(2, 1250.0, 1.0, 3.5)),
    )
    dialog = EQExportDialog(snap)
    captures = []
    def fake_save(parent, title, filename, file_filter, **kwargs):
        captures.append((parent, title, filename, file_filter, kwargs))
        return str(tmp_path / ("verified_eq." + format_name)), file_filter

    monkeypatch.setattr(QFileDialog, "getSaveFileName", fake_save)
    try:
        getattr(dialog, "choose_" + format_name)()
        assert len(captures) == 1
        assert captures[0][0] is dialog
        assert captures[0][4].get("options") == QFileDialog.Option.DontUseNativeDialog
        exported = tmp_path / ("verified_eq." + format_name)
        assert exported.is_file() and exported.stat().st_size > 50
        if format_name == "txt":
            data = exported.read_text(encoding="utf-8")
            assert "verified-trace" in data
            assert "1,200.0,-2.50,4.00" in data
            assert "2,1250.0,+1.00,3.50" in data
        else:
            assert exported.read_bytes().startswith(bytes((137, 80, 78, 71, 13, 10, 26, 10)))
    finally:
        dialog.close()
        app.processEvents()


def test_eq_cancel_dialog_does_not_create_files(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    snap = EQExportSnapshot("source", "House", 48000, 3.0, 1.0, (EQRow(1, 100., -2., 4.),))
    dialog = EQExportDialog(snap)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", "TXT (*.txt)"))
    try:
        dialog.choose_txt()
        assert not list(tmp_path.glob("*.txt")) and not list(tmp_path.glob("*.png"))
    finally:
        dialog.close()
        app.processEvents()
