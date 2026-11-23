from pathlib import Path
import time,traceback
from PIL import ImageGrab
from pywinauto import Desktop
root=Path(__file__).resolve().parent
report=[]
def write(msg):
    report.append(str(msg))
    (root/"V76_REAL_REF_SWITCH.log").write_text("\n".join(report),encoding="utf-8")
combo=None
try:
    w=Desktop(backend="uia").window(title_re=r"RemiX Auto Align V7\.6.*")
    assert w.exists() and w.is_visible()
    combo=w.descendants(control_type="ComboBox")[0]
    combo.select(1)
    time.sleep(.5)
    texts=[x.window_text() for x in w.descendants(control_type="Text")]
    target=[x for x in texts if "BÙ TƯƠNG ĐỐI TRACE" in x]
    delta=[x for x in texts if "Δ SUM–REF" in x]
    delay=[x for x in texts if "Shift TRACE" in x]
    assert target and "TRACE 1" in target[0],target
    assert delay and "TRACE 1" in delay[0] and "-4.80 ms" in delay[0],delay
    assert delta and "°" in delta[0],delta
    ImageGrab.grab(all_screens=False).save(root/"V76_REAL_REF2_GUI.png")
    write("LIVE_REF2_PASS "+repr((target[0],delta[0],delay[0])))
except Exception as exc:
    write("LIVE_REF2_FAIL "+str(exc)+"\n"+traceback.format_exc())
finally:
    if combo is not None:
        try:
            combo.select(0)
            time.sleep(.4)
            texts=[x.window_text() for x in w.descendants(control_type="Text")]
            target=[x for x in texts if "BÙ TƯƠNG ĐỐI TRACE" in x]
            delay=[x for x in texts if "Shift TRACE" in x]
            assert target and "TRACE 2" in target[0],target
            assert delay and "TRACE 2" in delay[0] and "+4.80 ms" in delay[0],delay
            write("RESTORED_REF1_PASS "+repr((target[0],delay[0])))
        except Exception as exc:
            write("RESTORE_REF1_FAIL "+str(exc)+"\n"+traceback.format_exc())
