"""RemiX Signal V8.11 UI + smoothing config QA, isolated from live Smaart."""
from pathlib import Path
import tempfile
from unittest.mock import patch
import numpy as np
from PyQt6.QtWidgets import QApplication,QWidget
from overlay_v7 import App
from trf_core import read_trf,auto_align
from smaart_smooth_sync_v811 import read_saved_smooth

root=Path(__file__).resolve().parent
saved=read_saved_smooth()
print("LIVE_SAVED_SMOOTH",saved,flush=True)
assert saved is not None and saved.mag_id==5 and saved.phase_id==5
assert abs(saved.mag_oct-1/6)<1e-8 and abs(saved.phase_oct-1/6)<1e-8
app=QApplication([])
w=App(demo=False)
w.timer.stop()
w.show()
app.processEvents()
print("TABS",w.tabs.count(),[w.tabs.tabText(i) for i in range(w.tabs.count())])
assert w.tabs.count()==2
assert w.mag.isChecked() and w.phase.isChecked() and w.mag_fit.isChecked()
assert not w.mag.isVisible() and not w.phase.isVisible() and not w.mag_fit.isVisible()
assert not w.mag_smooth.isVisible() and not w.phase_smooth.isVisible()
assert abs(float(w.mag_smooth.currentData())-1/6)<1e-8
assert abs(float(w.phase_smooth.currentData())-1/6)<1e-8
assert w.width()==205 and w.height()==463,(w.width(),w.height())
for ix in range(2):
    w.tabs.setCurrentIndex(ix)
    app.processEvents()
    filename=root/f"REMIX_SIGNAL_V811_TAB_{ix}.png"
    assert w.grab().save(str(filename))
    print("QA_SCREENSHOT",filename,flush=True)
    # The panel must not clip its axis and diagnostic controls.
    for widget in w.findChildren(QWidget):
        if not widget.isVisible() or widget is w:
            continue
        pos=widget.mapTo(w,widget.rect().topLeft())
        if pos.x()<0 or pos.y()<0 or pos.x()+widget.width()>w.width()+1 or pos.y()+widget.height()>w.height()+1:
            raise AssertionError(("OUTSIDE",ix,type(widget).__name__,
                                  widget.objectName(),pos.x(),pos.y(),
                                  widget.width(),widget.height()))
print("V811_TABS_2_NO_OVERFLOW_PASS")
# Both output layers must not be user-disableable from hidden controls
w.mag.setChecked(False)
w.phase.setChecked(False)
w.mag_fit.setChecked(False)
w.refresh_visibility()
assert all(x.isChecked() for x in (w.mag,w.phase,w.mag_fit))
print("ALWAYS_VISIBLE_AND_AUTO_FIT_LOCKED_PASS")
p=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(read_trf(p/n) for n in ("SUb.trf","FULL.trf"))
w.current_pair=(str(a.path),str(b.path))
w.current_traces=(a,b)
w.recalc()
w.align()
assert abs(w.delay.value()-13.2)<.15
assert w.current_sum is not None
assert all(x.isChecked() for x in (w.mag,w.phase,w.mag_fit))
print("SUM_AND_ALIGN_UNCHANGED_PASS",w.delay.value())
# Simulate Smaart saving new plot smoothing (never touch actual user XML)
with tempfile.TemporaryDirectory() as folder:
    xml=Path(folder)/"SmaartConfig.xml"
    def save(mag,phase):
        xml.write_text(f"""<root><plotProperties>
         <name>Phase1</name><visible>1</visible><smoothingId>{phase}</smoothingId>
         </plotProperties><plotProperties>
         <name>Magnitude1</name><visible>1</visible><smoothingId>{mag}</smoothingId>
         </plotProperties></root>""",encoding="utf8")
    save(4,5)
    assert read_saved_smooth(xml).mag_oct==1/12
    import smaart_smooth_sync_v811 as module
    with patch.object(module,"CONFIG",xml):
        w._refresh_saved_smoothing(force=True)
        assert float(w.mag_smooth.currentData())==1/12
        assert float(w.phase_smooth.currentData())==1/6
        assert w.mag_fit.isChecked()
        assert w.current_sum is not None
        print("CONFIG_WATCH_ID4_TO_1_12_PASS")
        save(5,5)
        w._refresh_saved_smoothing(force=True)
        assert abs(float(w.mag_smooth.currentData())-1/6)<1e-8
        assert abs(float(w.phase_smooth.currentData())-1/6)<1e-8
        print("CONFIG_WATCH_RESTORE_ID5_PASS")
        save(95,95)
        assert read_saved_smooth(xml) is None
        w._refresh_saved_smoothing(force=True)
        assert float(w.mag_smooth.currentData())==1/6
        print("UNSUPPORTED_ID_FAIL_CLOSED_PASS")
w.close();app.processEvents()
print("V811_AUTO_SMOOTH_COMPACT_QA_ALL_PASS",flush=True)
