from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import win32gui
from dock_geometry_v815 import read_smaart_anchors,compute_dock_rects,SidebarAnchors
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from trf_core import read_trf
root=Path(__file__).resolve().parent
app=QApplication([])
engine=App(demo=False)
engine.timer.stop()
hub=ToolHub(engine)
hub.timer.stop()
app.processEvents()
h=win32gui.FindWindow(None,"Smaart Suite")
rect=win32gui.GetWindowRect(h)
anchor=read_smaart_anchors(h)
assert anchor is not None,(h,anchor)
hub._anchors=anchor
hub._last_host_rect=rect
assert hub._update_placements(rect)
app.processEvents()
tool_bounds=(hub.x(),hub.y(),hub.width(),hub.height())
panel_bounds=(hub.dock.x(),hub.dock.y(),hub.dock.width(),hub.dock.height())
print("TOOL_AND_PANEL",tool_bounds,panel_bounds,"ANCHORS",anchor,flush=True)
assert tool_bounds[0]+tool_bounds[2]<panel_bounds[0]
assert panel_bounds[1]>anchor.tf_bottom
assert panel_bounds[1]+panel_bounds[3]<anchor.view_top
assert hub.height()==66 and hub.width()==205
assert hub.dock.width()==205
assert hub.dock.heading.text()=="AUTO PHASE"
assert hub.dock.stack.count()==3
assert hub.dock.stack.currentWidget() is engine
assert hub.dock.grab().save(str(root/"V815_DOCK_AUTO_PHASE.png"))
assert hub.grab().save(str(root/"V815_TOP_TOOLBAR.png"))
f=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(f/n) for n in ("SUb.trf","FULL.trf"))
engine.current_traces=(a,b)
engine.current_pair=(str(a.path),str(b.path))
engine.recalc();engine.align()
assert abs(engine.delay.value()-13.2)<.2
for mode,name in (("phase","AUTO PHASE"),
                  ("eq","AUTO EQ"),
                  ("fir","FIR"),
                  ("eq","AUTO EQ"),
                  ("phase","AUTO PHASE")):
    hub.select(mode)
    app.processEvents()
    assert hub.dock.heading.text()==name
    assert hub.dock.stack.currentWidget() is hub.pages[mode]
    assert hub.dock.height()<=anchor.view_top-anchor.tf_bottom
    assert hub.dock.scroll.viewport().height()<=hub.dock.height()
    assert hub.dock.scroll.verticalScrollBar().maximum()>=0
    if mode=="eq":
        hub.eq.compute()
        assert hub.eq.result is not None
        assert hub.dock.scroll.verticalScrollBar().maximum()>0
        assert hub.dock.grab().save(str(root/"V815_DOCK_AUTO_EQ.png"))
    elif mode=="fir":
        hub.fir.compute()
        assert hub.fir.result is not None
        assert hub.dock.scroll.verticalScrollBar().maximum()>0
        assert hub.dock.grab().save(str(root/"V815_DOCK_FIR.png"))
    print("MODE_PASS",mode,"scroll max",
          hub.dock.scroll.verticalScrollBar().maximum(),flush=True)
assert abs(engine.delay.value()-13.2)<.2
# Resize Smaart simulation: loss of safe right panel space must hide dock.
bad=SidebarAnchors(anchor.tf_bottom,anchor.tf_bottom+145,anchor.sidebar_left)
assert compute_dock_rects(rect,bad,(0,0,1920,1040)) is None
print("FAIL_CLOSED_SHORT_SIDEBAR_PASS",flush=True)
# synthetic host moves to 130px right (while screen clamps)
changed=(rect[0]+15,rect[1]+20,rect[2]+15,rect[3])
new=compute_dock_rects(changed,anchor,(0,0,1920,1040))
assert new and new.panel[1]+new.panel[3]<anchor.view_top
print("SMALL_RESIZE_GEOMETRY_PASS",new,flush=True)
hub.close()
app.processEvents()
print("V815_TOP_TOOLBAR_RIGHT_DOCK_ALL_PASS",flush=True)
