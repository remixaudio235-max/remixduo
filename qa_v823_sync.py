"""V8.23 regression: verified pair persistence and Windows named mutex.
No physical generator, soundcard, Smaart writes, or scroll commands.
"""
from pathlib import Path
from types import SimpleNamespace
import subprocess, sys, time
from PyQt6.QtWidgets import QApplication
from live_sync_v7 import SyncResult
from overlay_v7 import App
from signal_tools_gui_v813 import ToolHub
from single_instance_v823 import acquire_instance
import win32gui

m=acquire_instance()
assert m is not None,"Already running lock unexpectedly set by another V8.23!"
child=subprocess.run([sys.executable,"-c",
    "from single_instance_v823 import acquire_instance; "
    "print('LOCK_REJECTED' if acquire_instance() is None else 'BAD_SECOND_INSTANCE')"],
    cwd=str(Path(__file__).resolve().parent),text=True,capture_output=True,timeout=12)
assert child.returncode==0 and "LOCK_REJECTED" in child.stdout,(child.stdout,child.stderr)
print("SINGLE_INSTANCE_MUTEX_PASS",flush=True)

app=QApplication([])
e=App(False)
e.timer.stop()
hub=ToolHub(e)
hub.timer.stop()
hub.native_eq.timer.stop()
files=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a,b=(files/"4,8 ms delay-1.trf",files/"0 delay-1.trf")
assert a.is_file() and b.is_file()
names=(str(a),str(b))
verified=SyncResult(names,"FULL SCAN 108/108 in 1.00s",108,108,True,time.perf_counter())
e.found(verified)
until=time.monotonic()+5
while not e.current_traces and time.monotonic()<until:
    app.processEvents()
    time.sleep(.025)
assert e.controller.last_pair==names
assert e._selection_verified
assert e.current_traces and e.current_sum
print("VERIFIED_PAIR_LOADED_PASS",names,flush=True)
generation=e.controller.generation
source_sum=e.current_sum
# A screenshot/read failure is NEVER confirmation that the user unchecked.
transient=[
    SyncResult(None,"READ ERROR: PrintWindow not available",108,108,True,time.perf_counter()),
    SyncResult(None,"Scroll changed during capture; invalidated",108,108,True,time.perf_counter()),
    SyncResult(None,"Verified 93/108 rows, active 2",93,108,True,time.perf_counter()),
]
for r in transient:
    e.found(r)
    assert e.controller.last_pair==names
    assert e.controller.generation==generation
    assert e.current_sum is source_sum
    assert not e._selection_verified
    assert not e.graph_phase.isVisible()
    assert not e.graph_mag.isVisible()
print("TRANSIENT_FAILURE_PRESERVES_PAIR_BUT_HIDES_SUM_PASS",flush=True)
# Reverified unchanged pair must restore without reloading.
e.found(SyncResult(names,"Verified 108/108 rows, active 2",
                   108,108,True,time.perf_counter()))
assert e._selection_verified
assert e.controller.generation==generation
assert e.current_sum is source_sum
print("REVERIFIED_SAME_PAIR_NO_RELOAD_PASS",flush=True)
# Complete 108/108 but only 1 enabled is definitive, so old pair is invalidated.
e.found(SyncResult(None,"Verified 108/108 rows, active 1",
                   108,108,True,time.perf_counter()))
assert e.controller.last_pair is None
assert e.current_sum is None
assert e.controller.generation==generation+1
print("FULL_VERIFIED_UNCHECK_INVALIDATES_PASS",flush=True)
# Mock focus through same method used by real live polling gate.
target=SimpleNamespace(hwnd=4567,foreground=False)
e._target_is_foreground=lambda hwnd:hwnd==4567
assert e.should_poll_selection(target)  # companion owns foreground
e._target_is_foreground=lambda hwnd:False
assert not e.should_poll_selection(target)  # unrelated app owns foreground
print("COMPANION_FOCUS_ALLOWS_POLL_PASS",flush=True)
hub.close()
app.processEvents()
print("V823_SYNC_FOCUS_SINGLETON_ALL_PASS",flush=True)
