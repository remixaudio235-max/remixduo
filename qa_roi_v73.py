from pathlib import Path
from types import SimpleNamespace
from math import isclose
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt,QPoint
from PyQt6.QtGui import QImage
from PyQt6.QtTest import QTest
from roi_markers_v73 import hz_to_x,x_to_hz,bound_drag,ROIMarker
from trf_core import read_trf
from overlay_v7 import App

# Pure frequency/coordinate mapping: 20Hz...20kHz in log axis
for hz in (20,31.5,60,80,120,169,200,250,500,1000,4000,20000):
    x=hz_to_x(hz,252,1442)
    recovered=x_to_hz(x,252,1442)
    assert abs(recovered-hz) < hz*1e-9,(hz,x,recovered)
assert bound_drag("LF",500,60,200)<200
assert bound_drag("HF",40,60,200)>60
print("PASS_ROI_LOG_MAPPING_AND_CLAMPS")

app=QApplication([])
widget=App(demo=False)
widget.timer.stop()
assert widget.lf.value()==60 and widget.hf.value()==200
assert widget.roi_markers["LF"].windowFlags() & Qt.WindowType.FramelessWindowHint
assert not (widget.roi_markers["LF"].windowFlags() & Qt.WindowType.WindowTransparentForInput), "Marker must receive drag"
assert widget.graph_phase.windowFlags() & Qt.WindowType.WindowTransparentForInput
print("PASS_GRAPH_CLICK_THROUGH_AND_DRAG_HANDLE")

folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
widget.current_traces=(read_trf(folder/"623.trf"),read_trf(folder/"TUNNING M-1.trf"))
widget.recalc()
initial=widget.current_sum
widget.plot_layout=SimpleNamespace(phase=(252,112,1442,398),
                                   mag=(252,553,1442,398))
widget._apply_plot_layout()
app.processEvents()
for k in ("LF","HF"):
    marker=widget.roi_markers[k]
    assert marker.isVisible(),k
    assert marker.geometry().height()==ROIMarker.HEIGHT
    assert marker.cursor().shape()==Qt.CursorShape.SizeHorCursor
assert widget.graph_phase.isVisible()
assert widget.graph_mag.isVisible()
print("PASS_LF_HF_GRIPS_VISIBLE",widget.roi_markers["LF"].pos(),widget.roi_markers["HF"].pos())

widget.on_roi_drag("LF",hz_to_x(120,252,1442))
assert isclose(widget.lf.value(),120,abs_tol=.2)
assert widget.graph_phase.lf_hz==widget.graph_mag.lf_hz==widget.lf.value()
assert widget.current_sum is initial,"Dragging should not recalc SUM"
widget.on_roi_drag("HF",hz_to_x(500,252,1442))
assert isclose(widget.hf.value(),500,abs_tol=.3)
assert widget.graph_phase.hf_hz==widget.graph_mag.hf_hz==widget.hf.value()
print("PASS_LIVE_DRAG_TO_SPIN_SYNC",widget.lf.value(),widget.hf.value())

widget.on_roi_drag("LF",hz_to_x(1500,252,1442))
assert widget.lf.value()<widget.hf.value()
widget.on_roi_drag("HF",hz_to_x(30,252,1442))
assert widget.hf.value()>widget.lf.value()
print("PASS_CROSSING_PREVENTION",widget.lf.value(),widget.hf.value())

widget.lf.setValue(60)
widget.hf.setValue(200)
widget.last_solve=[object()]
widget.roi_markers["LF"].set_frequency(60)
widget.on_roi_drag("LF",hz_to_x(90,252,1442))
assert widget.last_solve is None,"Old AutoAlign results must invalidate after changing ROI"
assert "ROI changed" in widget.status.text()
print("PASS_ALIGN_ROI_DIRTY_INVALIDATION")

phase=widget.graph_phase
mag=widget.graph_mag
phase_img=QImage(1442,398,QImage.Format.Format_ARGB32)
phase_img.fill(0)
phase.render(phase_img)
mag_img=QImage(1442,398,QImage.Format.Format_ARGB32)
mag_img.fill(0)
mag.render(mag_img)
assert phase_img.save("V73_LF_HF_PHASE_QA.png")
assert mag_img.save("V73_LF_HF_MAG_QA.png")
print("PASS_RENDER_WITH_DASHED_ROI_GUIDES",phase.lf_hz,phase.hf_hz)
widget.timer.stop()
widget.close()
app.processEvents()
print("V73_ROI_UNIT_AND_GUI_PASS")
