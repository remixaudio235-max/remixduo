# -*- coding: utf-8 -*-
"""V11 draw proof: MagEq is painted by ORIGINAL SUM Magnitude QWidget.

Native Smaart only read via PrintWindow. Does not show a second EQ app.
"""
import os,time
os.environ["QT_QPA_PLATFORM"]="offscreen"
from pathlib import Path
import numpy as np,win32gui
from PIL import Image
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from native_eq_mag_v06 import native_fit_worker, FitFrame
from smaart_native_mag_fit import fit_native_mag
from trf_core import read_trf
DATA=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
ROOT=Path(__file__).resolve().parent
app=QApplication([])
engine=App(False);engine.timer.stop()
hub=ToolHub(engine);hub.timer.stop();hub.native_eq.timer.stop()
files=("4,8 ms delay-1.trf","0 delay-1.trf")
traces=tuple(read_trf(DATA/name) for name in files)
engine.current_pair=tuple(str(t.path) for t in traces)
engine.current_traces=traces
engine.recalc()
assert engine.current_sum is not None
assert engine.graph_mag.data is not None
hub.select("eq");hub.show();app.processEvents()
assert not hub.eq.plot.isVisible()
assert hub.native_eq.isHidden()
assert not engine.graph_phase.isVisible()
assert not engine.graph_mag.isVisible()
hub.eq.fs.setCurrentIndex(2)
hub.eq.target.setCurrentText("House")
hub.eq.source.setCurrentIndex(0)
hub.eq.compute()
deadline=time.monotonic()+15
while hub.eq.result is None and time.monotonic()<deadline:
    app.processEvents();time.sleep(.01)
assert hub.eq.result and hub.eq.result.status=="PREVIEW_READY"
src=hub.native_eq.source
assert src is not None and src.name.startswith("MagEq [")
assert len(src.peqs)==4
hwnd=win32gui.FindWindow(None,"Smaart Suite")
assert hwnd
frame=native_fit_worker(hwnd,src)
if frame is None:
    # Smaart may currently be minimized at (-32000,-32000). QA must not
    # restore the physical user's window. Use a validated historical frame.
    ref=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_9_NATIVE_AXIS_CAL_QA\V79_LIVE_SMAART_GUI.png')
    image=Image.open(ref)
    rect=(252,553,1442,398)
    fit=fit_native_mag(image,rect,(0,0,image.width,image.height),
              src.freqs,src.original_db,src.coh,trace_color='cyan')
    assert fit.accepted,fit.reason
    frame=FitFrame(src.revision,rect,fit,'cyan',time.monotonic())
    print('V11_HISTORICAL_SMAART_FRAME_OFFLINE_QA_ONLY',flush=True)
assert frame is not None and frame.fit.accepted
hub.native_eq.frame=frame
hub.native_eq._sync_sum_renderer()
app.processEvents()
assert engine.graph_mag.mageq_source is src
assert engine.graph_mag.mageq_frame is frame
assert engine.graph_mag.isVisible()
assert hub.native_eq.isHidden(),"No second MagEq QWidget may open"
assert engine.graph_phase.isHidden(),"Phase SUM must stay hidden in Auto EQ"
assert engine.graph_mag.geometry().getRect()==frame.plot
count=engine.graph_mag.mageq_draw_count
png=ROOT/"QA_V11_MAG_EQ_DRAWN_IN_SUMGRAPH.png"
assert engine.graph_mag.grab().save(str(png))
app.processEvents()
assert engine.graph_mag.mageq_draw_count>count
im=np.asarray(Image.open(png).convert("RGB"))
# Pixel colors expected for the MagEq amber line, not old neon-green SUM.
amber=(im[:,:,0]>=190)&(im[:,:,1]>=110)&(im[:,:,2]>=45)&(im[:,:,2]<175)
assert int(amber.sum())>500,int(amber.sum())
print("V11_MAGEQ_VISUAL_PAINT_PASS",frame.plot,frame.fit.score,
      "draws",engine.graph_mag.mageq_draw_count,"amber_pixels",amber.sum(),flush=True)
hub.eq.mageq_toggle.setChecked(False);app.processEvents()
assert engine.graph_mag.mageq_source is None
assert not engine.graph_mag.isVisible()
hub.eq.mageq_toggle.setChecked(True)
hub.native_eq._sync_sum_renderer();app.processEvents()
assert engine.graph_mag.mageq_source is src
hub.select("phase");app.processEvents()
assert engine.graph_mag.mageq_source is None
assert engine.graph_mag.data is not None
print("V11_A_B_SOURCE_UNCHANGED_AND_RETURN_SUM_PASS",flush=True)
hub.close();app.processEvents()
