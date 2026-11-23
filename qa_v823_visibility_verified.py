"""V8.22 Native Qt visibility / geometry / switching tests.
No Smaart inputs clicked, generator silent, no DSP writes.
"""
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from dock_geometry_v815 import compute_dock_rects,read_smaart_anchors
from trf_core import read_trf
import win32gui
app=QApplication([])
engine=App(False); engine.timer.stop()
hub=ToolHub(engine);hub.timer.stop();hub.native_eq.timer.stop()
root=Path(__file__).resolve().parent
hwnd=win32gui.FindWindow(None,"Smaart Suite")
assert hwnd
anchors=read_smaart_anchors(hwnd)
host=win32gui.GetWindowRect(hwnd)
screen=(0,0,1920,1040)
rects=compute_dock_rects(host,anchors,screen)
print("NATIVE_SMAART_GEOMETRY",host,rects,flush=True)
assert rects
assert rects.panel[3]>385,(rects.panel,anchors)
assert anchors.view_top>rects.panel[1]+rects.panel[3]
hub._anchors=anchors
hub._last_host_rect=host
assert hub._update_placements(host)
app.processEvents()
hub.select("phase")
assert hub.dock.height()==rects.panel[3]
assert hub.dock.heading.text()=="AUTO PHASE"
assert hub.dock.live_btn.isVisible()
assert hub.dock.hide_btn.isVisible()
assert hub.dock.auto_hide_btn.isChecked()
assert hub.dock.grab().save(str(root/"V822_TOP3_EXPANDED.png"))
data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(data/n) for n in ("SUb.trf","FULL.trf"))
engine.current_pair=(str(a.path),str(b.path))
engine.current_traces=(a,b)
engine._selection_verified=True  # QA fixture verified full pair
engine.recalc()
assert engine.current_sum is not None
# Model plots are visible only when plot boxes exist.
engine.overlay_positioned=True
engine.plot_layout=None
hub.select("phase"); app.processEvents()
assert engine.graph_mag.isVisible()
assert engine.graph_phase.isVisible()
assert all(g.isVisible() for g in engine.roi_line_grips.values())
# FIR work must hide SUM/MagEq and ROI, while FIR page is current.
hub.select("fir"); app.processEvents()
assert hub.active=="fir" and hub.dock.stack.currentWidget() is hub.fir
assert not engine.graph_mag.isVisible() and not engine.graph_phase.isVisible()
assert not any(g.isVisible() for g in engine.roi_line_grips.values())
assert not hub.native_eq.isVisible()
print("FIR_ONLY_NO_SUM_OVERLAY_PASS",flush=True)
# AutoEQ page without valid MagEQ data must not leak a phase/SUM trace.
hub.select("eq"); app.processEvents()
assert hub.active=="eq" and not engine.graph_phase.isVisible()
assert not engine.graph_mag.isVisible()
assert not any(m.isVisible() for m in engine.roi_markers.values())
print("AUTO_EQ_NO_STALE_SUM_PASS",flush=True)
# Hide works for whichever tool is active and is not reversed on tick.
hub.hide_workspace(); app.processEvents()
assert hub.isVisible() and not hub.dock.isVisible()
assert not hub.workspace_visible and not engine.overlay_workspace_visible
assert not engine.graph_mag.isVisible() and not engine.graph_phase.isVisible()
assert not hub.native_eq.isVisible()
assert not any(g.isVisible() for g in engine.roi_line_grips.values())
hub._update_placements(host);app.processEvents()
assert not hub.dock.isVisible()
print("HIDE_WORKSPACE_ALL_RENDERERS_PASS",flush=True)
# Reopen phase with one click.
hub.select("phase");app.processEvents()
assert hub.workspace_visible and hub.dock.isVisible()
assert engine.graph_phase.isVisible()
print("REOPEN_PHASE_PASS",flush=True)
# LIVE always means native Smaart only; toolbar remains for re-entry.
hub.dock.live_btn.click();app.processEvents()
assert hub.active is None
assert hub.isVisible() and not hub.dock.isVisible()
assert not engine.graph_phase.isVisible() and not engine.graph_mag.isVisible()
assert not any(g.isVisible() for g in engine.roi_line_grips.values())
hub._update_placements(host)
assert not hub.dock.isVisible()
print("RETURN_TUNING_LIVE_PASS",flush=True)
# EQ after LIVE then FIR must not show EQ Mag nor phase.
hub.select("eq");hub.select("fir");app.processEvents()
assert not engine.graph_mag.isVisible() and not engine.graph_phase.isVisible()
# Toggle auto-hide is truly controllable, not ornamental.
hub.dock.auto_hide_btn.click()
assert not hub.auto_hide_enabled
hub.dock.auto_hide_btn.click()
assert hub.auto_hide_enabled
print("AUTO_HIDE_CONTROL_PASS",flush=True)
hub.close();app.processEvents()
print("V822_NATIVE_QT_FULL_VISIBILITY_AND_TOP3_ALL_PASS",flush=True)
