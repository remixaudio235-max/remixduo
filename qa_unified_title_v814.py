from pathlib import Path
from PyQt6.QtCore import Qt,QEvent,QPointF,QPoint
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from trf_core import read_trf
import win32gui
root=Path(__file__).resolve().parent
app=QApplication([])
engine=App(False);engine.timer.stop()
hub=ToolHub(engine);hub.timer.stop()
app.processEvents()
h=win32gui.FindWindow(None,"Smaart Suite")
assert h
path=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(path/n) for n in ("SUb.trf","FULL.trf"))
engine.current_pair=(str(a.path),str(b.path))
engine.current_traces=(a,b)
engine.recalc();engine.align()
assert hub.width()==205
assert hub.windowFlags()&Qt.WindowType.FramelessWindowHint
assert hub.title_bar.isVisible()
assert not engine.header.isVisible()
assert hub.stack.count()==3
assert len(hub.buttons)==3
assert all(p.parent() is hub.stack for p in (engine,hub.eq,hub.fir))
for mode,fn in (("phase","V814_UNIFIED_PHASE.png"),
                ("eq","V814_UNIFIED_EQ.png"),
                ("fir","V814_UNIFIED_FIR.png")):
    hub.select(mode)
    if mode=="eq":
        hub.eq.compute()
        assert hub.eq.result is not None
    if mode=="fir":
        hub.fir.compute()
        assert hub.fir.result is not None
    app.processEvents()
    assert hub.active==mode
    assert hub.stack.currentWidget() is hub.pages[mode]
    assert hub.stack.count()==3
    assert hub.isVisible()
    shown=[x.isVisible() for x in (engine,hub.eq,hub.fir)]
    assert sum(shown)==1,(mode,shown)
    assert hub.height()==73+hub._page_heights[mode],hub.height()
    assert hub.title_bar.y()==0
    assert hub.nav_frame.y()==33
    assert hub.stack.y()==73,hub.stack.y()
    assert hub.grab().save(str(root/fn))
    print("V814_UNIFIED",mode,hub.size().width(),hub.size().height(),shown,flush=True)
    # No root-level child text beyond application boundaries.
    for child in (hub.title_bar,hub.nav_frame,hub.stack,hub.close_button):
        top=child.mapTo(hub,child.rect().topLeft())
        assert top.x()>=0 and top.y()>=0,(mode,child,top)
        assert top.x()+child.width()<=hub.width()+1,(mode,child,top,child.width())
        assert top.y()+child.height()<=hub.height()+1,(mode,child,top,child.height())
# Default DOCK must anchor relative to native Smaart right edge:
rect=win32gui.GetWindowRect(h)
hub._dock(rect)
x=hub.x();y=hub.y()
assert x>=rect[2]-hub.width()-12,(x,rect)
print("V814_DOCK_RIGHT",x,y,"HOST_RIGHT",rect[2],flush=True)
# Drag custom title by +12px, +15px, then repositioning remains manual
origin=hub.pos()
pressed=QMouseEvent(QEvent.Type.MouseButtonPress,QPointF(35,12),
    QPointF(float(origin.x()+35),float(origin.y()+12)),
    Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
hub.eventFilter(hub.title_bar,pressed)
moved=QMouseEvent(QEvent.Type.MouseMove,QPointF(15,27),
    QPointF(float(origin.x()+15),float(origin.y()+27)),
    Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
hub.eventFilter(hub.title_bar,moved)
released=QMouseEvent(QEvent.Type.MouseButtonRelease,QPointF(15,27),
    QPointF(float(origin.x()+15),float(origin.y()+27)),
    Qt.MouseButton.LeftButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier)
hub.eventFilter(hub.title_bar,released)
assert hub._manually_placed
assert hub.x()==x-20 and hub.y()==y+15,(hub.pos(),origin)
print("V814_TITLE_DRAG_PASS",hub.pos(),flush=True)
hub.close()
app.processEvents()
print("V814_SINGLE_WINDOW_TITLE_LAYOUT_QA_PASS",flush=True)
