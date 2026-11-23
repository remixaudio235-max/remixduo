"""V8.63 UI branding/layout QA, no Smaart/hardware effects."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from autoeq_export_dialog_v08 import EQExportDialog,EQExportSnapshot,EQRow

def test_duo_three_primary_tools_no_top_export():
    app=QApplication.instance() or QApplication([])
    engine=App(demo=True);engine.timer.stop()
    hub=ToolHub(engine);hub.timer.stop();hub.native_eq.timer.stop()
    try:
        assert hub.brand_text.text()=="RemiX Duo"
        # V8.107: the LAN "Điều khiển" tab was removed; three audio tools.
        assert set(hub.buttons)=={"phase","eq","fir"}
        assert [b.text() for b in hub.buttons.values()]==[
            "Auto Phase","Auto EQ","Auto FIR"]
        assert hub.width()==205
        assert hub.eq.export.text()=="Xuất EQ"
        assert not any("Xuất EQ" in a.text() for a in hub.menu_button.menu().actions())
        hub.select("fir")
        assert hub.active=="fir"
        assert hub.dock.heading.text()=="AUTO FIR"
        hub._set_toolbar_mode("compact")
        assert hub.buttons["fir"].text()=="A.FIR"
        hub._set_toolbar_mode("mini")
        assert hub.buttons["fir"].text()=="FIR"
        hub._set_toolbar_mode("menu")
        assert hub.menu_button.isVisible() or not hub.isVisible()
        hub._set_toolbar_mode("full")
        assert hub.buttons["fir"].text()=="Auto FIR"
    finally:
        hub.close();app.processEvents()

def test_export_has_frameless_duo_header_and_contextual_saves():
    app=QApplication.instance() or QApplication([])
    snap=EQExportSnapshot("TUNNINNGGG-9","Flat",48000,5.1,4.2,
        (EQRow(1,189.3,-8.31,8.0),))
    dlg=EQExportDialog(snap)
    try:
        dlg.show();app.processEvents()
        assert dlg.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert dlg.titlebar.isVisible()
        assert dlg.title_close.isVisible()
        assert dlg.title_close.toolTip()=="Đóng bảng EQ"
        assert dlg.brand_label.text()=="RemiX Duo"
        assert dlg.heading.text()=="BẢNG EQ VỪA TẠO"
        assert dlg.table.rowCount()==12
        assert dlg.table.columnCount()==4
        assert dlg.png_button.text()=="Lưu PNG"
        assert dlg.txt_button.text()=="Lưu TXT"
        assert dlg.height()==775
        assert "RemiX Duo" in snap.as_text()
        assert "RemiX Signal" not in snap.as_text()
        dlg.title_close.click()
        assert not dlg.isVisible()
    finally:
        dlg.close();app.processEvents()
