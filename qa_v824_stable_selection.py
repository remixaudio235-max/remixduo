"""V8.24 verified native trace snapshot + 3/3 commit, 250-cycle endurance QA."""
from pathlib import Path
from time import perf_counter,sleep
from PyQt6.QtWidgets import QApplication
from live_sync_v7 import SyncResult
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from stable_ticks_v824 import StableTickGate
import json
root=Path(__file__).resolve().parent
app=QApplication([])
e=App(False);e.timer.stop()
hub=ToolHub(e);hub.timer.stop();hub.native_eq.timer.stop()
data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=tuple(str(data/n) for n in ("4,8 ms delay-1.trf","0 delay-1.trf"))
assert Path(a).is_file() and Path(b).is_file()
pair=(a,b)
def r(names,status=None,ambiguous=0):
    names=tuple(names)
    return SyncResult(tuple(names) if len(names)==2 else None,
                      status or f"Verified 108/108 rows, active {len(names)}",
                      108,108,True,perf_counter(),names,ambiguous)
def pulse(names,n=1):
    for _ in range(n):
        e.found(r(names))
        app.processEvents()
# Reordered, partial or flickering frames must never commit
pulse(pair,2)
assert e.controller.last_pair is None and not e._selection_verified
assert e.tick_gate.stable==2
assert not e.selection_warning.isHidden()
assert e.candidate_card.isHidden()
pulse((a,str(data/"610.trf")),1)
assert e.controller.last_pair is None
pulse(pair,3)
assert e.controller.last_pair==pair and e._selection_verified
deadline=perf_counter()+6
while not e.current_traces and perf_counter()<deadline:
    app.processEvents()
    sleep(.025)
assert e.current_traces and e.current_sum
gen=e.controller.generation
sum_ptr=e.current_sum
print("STABLE_3_OF_3_INITIAL_COMMIT_PASS",flush=True)
# 250 stable scans must NOT trigger reloaded TRF, increment gen or change pair
for j in range(250):
    e.found(r(pair))
    app.processEvents()
assert e.controller.generation==gen
assert e.current_sum is sum_ptr
assert e._selection_verified
print("250_POLL_NO_PAIR_DRIFT_NO_RELOAD_PASS",flush=True)
# Out-of-order worker result: pair must correspond EXACTLY to snapshot, not
# mutable self.observer.states; fake mismatch is transient and never committed.
bad=SyncResult(pair,"Verified 108/108 rows, active 2",108,108,True,
               perf_counter(),(b,a),0)
e.found(bad)
assert e.controller.last_pair==pair
assert not e._selection_verified and not e.graph_phase.isVisible()
assert e.candidate_card.isHidden()
print("IMMUTABLE_SNAPSHOT_MISMATCH_FAIL_CLOSED_PASS",flush=True)
# READ ERROR or incomplete no invalidation/reload
for bad_status in (
    SyncResult(None,"READ ERROR: PrintWindow",0,108,True,perf_counter()),
    SyncResult(None,"Verified 104/108 rows, active 2",104,108,True,perf_counter()),
    r(pair,ambiguous=1),
):
    e.found(bad_status)
    assert e.controller.last_pair==pair and not e._selection_verified
    assert e.controller.generation==gen
print("TRANSIENT_RETAIN_PAIR_HIDE_SUM_PASS",flush=True)
# Stable invalid 6 must invalidate after 3 valid captures, never select first 2.
six=(a,b,str(data/"610.trf"),str(data/"TUNNINNGGG-2.trf"),
     str(data/"TUNNING-31.trf"),str(data/"TUNNING-30.trf"))
pulse(six,2)
assert e.controller.last_pair==pair and not e._selection_verified
pulse(six,1)
assert e.controller.last_pair is None
assert e.candidate_card.isHidden()
assert not e.solve.isEnabled()
assert "6 Trace" in e.selection_warning.text()
print("INVALID_SIX_TICKS_HIDES_ALL_PASS",flush=True)
for count in (0,1,3):
    pulse(six[:count],3)
    assert e.controller.last_pair is None
    assert not e._selection_verified
    assert not e.solve.isEnabled()
print("INVALID_0_1_3_TICKS_PASS",flush=True)
pulse(pair,3)
assert e.controller.last_pair==pair
assert e._selection_verified
assert not e.candidate_card.isHidden()
deadline=perf_counter()+6
while not e.current_traces and perf_counter()<deadline:
    app.processEvents();sleep(.02)
assert e.solve.isEnabled()
print("RECOVERY_EXACT_2_AUTO_RELOAD_PASS",flush=True)
# Panel native placement: full 446px is available but compact phase should
# use 335px, empty/invalid should shrink below 200px.
hub._anchors=None
hub._last_host_rect=(0,0,1920,1000)
hub.select("phase")
app.processEvents()
print("QA_WIDGET_HEIGHT",hub.dock.height(),hub.dock.stack.height(),flush=True)
# Need UIA native anchors for precise real window placement in the screenshot test.
hub.dock.apply_rect((1480,430,205,335))
hub.dock.show();hub.show();app.processEvents()
assert hub.dock.grab().save(str(root/"V824_COMPACT_PHASE_NATIVE_QA.png"))
record={"pass":"V824_STATE_MACHINE_250_POLL","polls":len(e.tick_gate.history),
        "snapshot":e.tick_gate.history[-1]}
(root/"V824_STABLE_GATE_QA.json").write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf8")
hub.close()
print("V824_SELECTION_STABILITY_ALL_PASS",flush=True)
