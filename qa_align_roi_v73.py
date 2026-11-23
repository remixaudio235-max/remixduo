from pathlib import Path
from PyQt6.QtWidgets import QApplication
from overlay_v7 import App
from trf_core import read_trf,auto_align
app=QApplication([])
a=App(demo=False)
a.timer.stop()
folder=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
pair=(read_trf(folder/"TUNNINNGGG-8.trf"),
      read_trf(folder/"TUNNINNGGG-7.trf"))
a.current_traces=pair
a.controller.apply(tuple(str(t.path) for t in pair),"QA saved trace pair")
a.current_traces=pair
a.lf.setValue(59.3)
a.hf.setValue(452.3)
a.recalc()
expected=auto_align(*pair,lf=59.3,hf=452.3,max_delay_ms=180)
a.align()
assert a.last_solve is not None
assert len(a.last_solve)==len(expected)
for actual,ref in zip(a.last_solve,expected):
    assert abs(actual.delay_ms-ref.delay_ms)<1e-8
    assert actual.invert_trace2 == ref.invert_trace2
assert abs(a.graph_mag.lf_hz-59.3)<1e-8
assert abs(a.graph_phase.hf_hz-452.3)<1e-8
print("PASS_AUTO_ALIGN_READS_VISUAL_LF_HF","LF",a.lf.value(),
      "HF",a.hf.value(),"TopK",len(a.last_solve),
      "TopDelayMS",a.last_solve[0].delay_ms,"ROI_BINS",a.last_solve[0].roi_bins)
a.close()
app.processEvents()
