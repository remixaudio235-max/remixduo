import sys,time,json
from pathlib import Path
if "pytest" in sys.modules:
    import pytest
    pytest.skip("standalone live Windows screenshot QA; not safe inside pytest",
                allow_module_level=True)
from PIL import ImageGrab
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from overlay_v7 import App
import win32gui,win32con

OUT=Path(__file__).resolve().parent
qt=QApplication(sys.argv)
gui=App(demo=True)
assert gui.host is not None
report={"steps":[]}
t0=time.perf_counter()

def step(name,index,expect_lines):
    gui.host.change(index)
    # Synchronous stale invalidation is critical on every tick transition.
    old_lines=bool(gui.graph_mag.data)
    if old_lines:raise AssertionError("STALE_LINE_NOT_CLEARED_IMMEDIATELY")
    qt.processEvents()
    deadline=time.perf_counter()+1.5
    while time.perf_counter()<deadline:
        qt.processEvents()
        if bool(gui.graph_mag.data)==expect_lines:break
        time.sleep(.02)
    current=gui.graph_mag.data
    loaded=bool(current)
    if loaded!=expect_lines:raise AssertionError((name,"loaded",loaded,"expected",expect_lines))
    if loaded:
        gui.graph_mag.grab();gui.graph_phase.grab()
        assert getattr(gui.graph_mag,"_last_points",0)>100
        assert getattr(gui.graph_phase,"_last_points",0)>100
        left=gui.graph_mag.data.sources
        if index==1:assert set(left)=={"QA_C.trf","QA_D.trf"}
    report["steps"].append({"name":name,"index":index,"has_mag":loaded,
       "has_phase":bool(gui.graph_phase.data),
       "generation":gui.controller.generation,
       "phase_path_points":getattr(gui.graph_phase,"_last_points",0),
       "mag_path_points":getattr(gui.graph_mag,"_last_points",0),
       "elapsed_ms":round((time.perf_counter()-t0)*1000,1),
       "source":(current.sources if current else None)})
    return current

# Settle initial asynchronous load.
deadline=time.perf_counter()+2
while time.perf_counter()<deadline and gui.graph_mag.data is None:
    qt.processEvents();time.sleep(.01)
assert gui.graph_mag.data is not None
report["initial"]=gui.graph_mag.data.sources

step("SWITCH_C_D",1,True)
step("ONE_TICK_FAIL_CLOSED",2,False)
step("THREE_TICKS_FAIL_CLOSED",3,False)
step("RESTORE_A_B",0,True)
step("SWITCH_C_D_AGAIN",1,True)

gui.align()
qt.processEvents()
report["top_k"]=len(gui.last_solve or [])
assert report["top_k"]==4
report["delay_ms"]=gui.delay.value()
report["invert"]=gui.invert.isChecked()
report["screen"]=str(OUT/"V7_QA_OVERLAY_WINDOWS_SCREEN.png")
# The windows overlay layer must be click-through, independent from panel.
exstyles=[]
for graph in (gui.graph_mag,gui.graph_phase):
    graph.show()
    qt.processEvents()
    hwnd=int(graph.winId())
    flags=win32gui.GetWindowLong(hwnd,win32con.GWL_EXSTYLE)
    exstyles.append({"hwnd":hwnd,"click_through":bool(flags & win32con.WS_EX_TRANSPARENT),
       "no_activate":bool(flags & win32con.WS_EX_NOACTIVATE)})
assert all(x["click_through"] for x in exstyles)
report["windows_overlays"]=exstyles
gui.host.raise_();gui.raise_()
qt.processEvents()
time.sleep(.20)
ImageGrab.grab().save(report["screen"])
report["result"]="PASS"
(OUT/"V7_QA_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("V7_WINDOWS_UI_QA_PASS",json.dumps(report,ensure_ascii=False))
gui.close()
qt.quit()

