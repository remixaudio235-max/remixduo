from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import threading,time
from PyQt6.QtWidgets import QApplication
from remix_duo.platforms.contracts import WindowRef,WindowState,SelectionEvidence

def state():return WindowState(WindowRef('darwin',5,'start','7'),(0,0,1000,800),'Smaart',True,True,'9.6')
def pump(app,duration=.15):
    deadline=time.monotonic()+duration
    while time.monotonic()<deadline:app.processEvents();time.sleep(.002)

def test_slow_selection_does_not_block_geometry_or_queue_more_scans():
    from remix_duo.ui.native_monitor import NativeMonitor
    app=QApplication.instance() or QApplication([])
    release=threading.Event();calls=[]
    class Backend:
        def list_windows(self):return [state()]
        def read_selection(self,ref):
            calls.append(ref);release.wait(2)
            return SelectionEvidence(ref,('a','b'),time.monotonic(),True,('a','b'))
    monitor=NativeMonitor(Backend())
    updates=[];monitor.geometry_changed.connect(updates.append)
    monitor.start();pump(app,.2)
    assert len(updates)>=2 and len(calls)==1
    release.set();monitor.close();pump(app)

def test_selection_completion_rejected_after_window_identity_changes():
    from remix_duo.ui.native_monitor import NativeMonitor
    app=QApplication.instance() or QApplication([])
    monitor=NativeMonitor(object());monitor.window=state();seen=[]
    monitor.selection_changed.connect(seen.append)
    original=monitor.window
    monitor.window=replace(original,ref=replace(original.ref,process_started='restart'))
    e=SelectionEvidence(original.ref,('a','b'),time.monotonic(),True,('a','b'))
    monitor.accept_selection(original,e,None)
    assert not seen
    monitor.close()

def test_native_diagnostics_does_not_invalidate_manual_trf_results():
    from remix_duo.ui.workspace import Workspace
    app=QApplication.instance() or QApplication([])
    class Backend:
        def list_windows(self):return []
    widget=Workspace(Backend());result=object();widget.result=result
    widget.native_monitor.selection_changed.emit(None)
    assert widget.result is result
    widget.close()
