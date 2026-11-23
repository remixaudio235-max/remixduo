"""V8.16: native Smaart Real Time / Impulse / SPL alignment QA."""
from pathlib import Path
from unittest.mock import patch
import time
import win32gui
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from dock_geometry_v815 import (read_smaart_anchors,compute_dock_rects,
                                SidebarAnchors)
from win_databar_v7 import MainWindow
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from trf_core import read_trf

root=Path(__file__).resolve().parent
hwnd=win32gui.FindWindow(None,"Smaart Suite")
assert hwnd
native=win32gui.GetWindowRect(hwnd)
a=read_smaart_anchors(hwnd)
assert a is not None,a
s=(0,0,1920,1040)
g=compute_dock_rects(native,a,s)
assert g and g.panel
print("NATIVE_UIA",native,a,g,flush=True)
# The toolbar must share EXACT same top/bottom line with the native buttons.
assert g.toolbar[1]==a.real_time[1]
assert g.toolbar[3]==a.real_time[3]-a.real_time[1]
assert g.toolbar[0]+g.toolbar[2]+3==a.real_time[0]
assert a.real_time[1]==a.impulse[1]==a.spl[1]
assert a.real_time[3]==a.impulse[3]==a.spl[3]
assert g.panel[1]>a.tf_bottom
assert g.panel[1]+g.panel[3]<a.view_top
print("SAME_ROW_NATIVE_BUTTONS_PASS",flush=True)
# Host moves right/down on a larger virtual desktop: buttons follow.
moved=(125,90,1920+125,1040+90)
gm=compute_dock_rects(moved,a,(0,0,2560,1440))
assert gm and gm.toolbar[0]==g.toolbar[0]+125
assert gm.toolbar[1]==g.toolbar[1]+90
assert gm.panel and gm.panel[1]==g.panel[1]+90
print("MOVE_FOLLOW_NATIVE_RELATIVE_PASS",gm,flush=True)
# Width changes while left edge stays fixed; toolbar remains left of RT.
for w in (1300,1550,1920,2300):
    host=(0,0,w,1040)
    screen=(0,0,2560,1440)
    d=compute_dock_rects(host,a,screen)
    assert d and d.toolbar[0]+d.toolbar[2]+3==a.real_time[0]+w-1920
    assert d.toolbar[1]==a.real_time[1]
print("RESIZE_WIDTH_SAME_ROW_PASS",flush=True)
# When sidebar becomes too short, only the dock disappears, NOT buttons.
small=(0,0,1920,775)
d=compute_dock_rects(small,a,s)
assert d and d.panel is None and d.toolbar[1]==a.real_time[1]
print("SHORT_SIDEBAR_TOOLBAR_REMAINS_PASS",flush=True)
from dataclasses import replace
no_tf=replace(a,tf_bottom=-1,view_top=-1)
no_panel=compute_dock_rects(native,no_tf,s)
assert no_panel and no_panel.panel is None and no_panel.toolbar==g.toolbar
print('TF_PANEL_HIDDEN_NATIVE_ROW_STILL_VISIBLE_PASS',flush=True)
# No safe room to the left of RealTime: do not cover native buttons.
narrow=(0,0,490,740)
assert compute_dock_rects(narrow,a,s) is None
print("NARROW_WIDTH_FAIL_CLOSED_PASS",flush=True)

app=QApplication([])
engine=App(False)
engine.timer.stop()
hub=ToolHub(engine)
hub.timer.stop()
hub._anchors=a
hub._last_host_rect=native
hub._last_hwnd=hwnd
hub._anchor_requested_at=time.monotonic()
hub._screen_rect=lambda: s
assert hub._update_placements(native)
app.processEvents()
assert hub.geometry().getRect()==g.toolbar
assert hub.width()==205 and hub.height()==30
assert hub.layout().count()==3,hub.layout().count()
assert set(hub.buttons)=={"phase","eq","fir"}
assert hub.dock.geometry().getRect()==g.panel
assert hub.grab().save(str(root/"V816_NATIVE_ROW_TOOLBAR.png"))
print("QT_TOPBAR_EXACT_NATIVE_ANCHOR_PASS",flush=True)
src=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
p,q=(read_trf(src/n) for n in ("SUb.trf","FULL.trf"))
engine.current_pair=(str(p.path),str(q.path))
engine.current_traces=(p,q)
engine.recalc();engine.align()
assert abs(engine.delay.value()-13.2)<.2
for name in ("phase","eq","fir","phase"):
    QTest.mouseClick(hub.buttons[name],Qt.MouseButton.LeftButton)
    app.processEvents()
    assert hub.active==name
    assert hub.dock.stack.currentWidget() is hub.pages[name]
    assert hub.geometry().getRect()==g.toolbar
    if name=="eq":
        hub.eq.compute()
        assert hub.eq.result is not None
    if name=="fir":
        hub.fir.compute()
        assert hub.fir.result is not None
print("THREE_TOOL_BUTTONS_AND_ENGINE_PRESERVED_PASS",flush=True)
# Mouse-driven resizing of the Smaart rectangle, without changing real
# Smaart GUI or audio hardware.
with patch("signal_tools_gui_v813.locate_smaart",
           return_value=MainWindow(hwnd,moved,True)):
    with patch("signal_tools_gui_v813.win32gui.GetWindowRect",
               return_value=moved):
        with patch.object(engine,"_target_is_foreground",return_value=True):
            hub._anchor_requested_at=time.monotonic()
            hub.tick()
            app.processEvents()
            assert hub.geometry().getRect()==gm.toolbar,hub.geometry().getRect()
print("LIVE_TICK_REPOSITIONS_ON_NATIVE_MOVE_PASS",flush=True)
# Recompute after moving host back.
assert hub._update_placements(native)
app.processEvents()
assert hub.geometry().getRect()==g.toolbar
hub.close()
app.processEvents()
print("V816_REALTIME_ROW_ALL_PASS",flush=True)
