"""V0.19: use only a fresh, same-HWND viewport fit; transient failures do not blink."""
import time
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import Future
from PyQt6.QtWidgets import QApplication
import pytest
import native_eq_mag_v06 as native

RECT=(200,100,1700,1000)
PLOT=(252,553,1442,398)
HWND=10923

class Geo:
    def __init__(self,rect):self.rect=rect
    def getRect(self):return self.rect

class Graph:
    def __init__(self):
        self.mageq_source=None;self.mageq_frame=None
        self.rect=PLOT;self.visible=False
        self.render_updates=0
    def isVisible(self):return self.visible
    def geometry(self):return Geo(self.rect)
    def setGeometry(self,*rect):self.rect=rect
    def set_mageq(self,source=None,frame=None):
        self.mageq_source=source;self.mageq_frame=frame
        self.render_updates+=1

class Engine:
    def __init__(self):
        self.graph_mag=Graph()
        self.refreshes=0
    def refresh_visibility(self):
        self.refreshes+=1
        self.graph_mag.visible=self.graph_mag.mageq_source is not None

@pytest.fixture
def running(monkeypatch):
    app=QApplication.instance() or QApplication([])
    assert app is not None
    state={"window":RECT,"front":HWND,"visible":True,"iconic":False}
    monkeypatch.setattr(native.win32gui,"FindWindow",lambda *args:HWND)
    monkeypatch.setattr(native.win32gui,"IsWindow",lambda h:h==HWND)
    monkeypatch.setattr(native.win32gui,"IsWindowVisible",lambda h:state["visible"])
    monkeypatch.setattr(native.win32gui,"IsIconic",lambda h:state["iconic"])
    monkeypatch.setattr(native.win32gui,"GetForegroundWindow",lambda:state["front"])
    monkeypatch.setattr(native.win32gui,"GetWindowRect",lambda h:state["window"])
    monkeypatch.setattr(native.win32process,"GetWindowThreadProcessId",
                        lambda h:(1,321 if h==HWND else 777))
    engine=Engine()
    # Native renderer must bind to the same verified HWND as the observer.
    engine.observer=SimpleNamespace(hwnd=HWND)
    hub=SimpleNamespace(engine=engine,active="eq",workspace_visible=True,
                        _last_hwnd=HWND,
                        isVisible=lambda:True,_eq_tick_safe=lambda:True)
    widget=native.NativeAutoEQMag(hub)
    widget.timer.stop()
    source=SimpleNamespace(revision=3)
    data=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data/0 delay-1.trf"
    stat=data.stat()
    token=(str(data),stat.st_mtime_ns,stat.st_size,7)
    source.source_identity="qa-native-identity"
    source.source_name=data.stem
    hub.eq=SimpleNamespace(_export_source_token=token,result=object(),
                           _verified_single=lambda:token)
    widget.approved_token=token
    widget.source=source
    widget.revision=3
    widget.last_submit=time.monotonic()
    frame=native.FitFrame(3,PLOT,object(),"blue",time.monotonic(),HWND,RECT,
                          source_identity="qa-native-identity",identity_verified=True)
    yield widget,engine,frame,state
    widget.timer.stop()
    widget.future=None
    widget.pool.shutdown(wait=False,cancel_futures=True)
    widget.hide();widget.close()

def completed(value):
    future=Future()
    future.set_result(value)
    return future

def test_transient_native_failed_capture_preserves_valid_mageq(running):
    widget,engine,frame,_=running
    widget.frame=frame
    widget._sync_sum_renderer()
    assert engine.graph_mag.isVisible()
    old_updates=engine.graph_mag.render_updates
    widget.future=completed(None)
    widget.tick()
    assert widget.frame is frame
    assert engine.graph_mag.isVisible()
    assert engine.graph_mag.render_updates==old_updates
    assert widget.last_native_drop=="Transient native fit failure"

def test_changed_native_window_geometry_rejects_cached_and_inflight(running):
    widget,engine,frame,state=running
    widget.frame=frame
    widget._sync_sum_renderer()
    state["window"]=(200,100,1800,1000)
    widget.future=completed(frame)
    widget.tick()
    assert widget.frame is None
    assert not engine.graph_mag.isVisible()
    assert engine.graph_mag.mageq_source is None

@pytest.mark.parametrize("transition", ["minimized","foreground","expired"])
def test_invalidated_native_context_hides_immediately(running,transition):
    widget,engine,frame,state=running
    widget.frame=frame
    widget._sync_sum_renderer()
    if transition=="minimized":state["iconic"]=True
    if transition=="foreground":state["front"]=70112
    if transition=="expired":
        widget.frame=native.FitFrame(3,PLOT,object(),"blue",
                time.monotonic()-4,HWND,RECT)
    widget.tick()
    assert widget.frame is None
    assert not engine.graph_mag.isVisible()

def test_old_hwnd_rejected_even_if_plot_geometry_matches(running):
    widget,engine,frame,_=running
    stale=native.FitFrame(3,PLOT,object(),"blue",time.monotonic(),99999,RECT)
    assert not native.frame_is_fresh_for_window(stale,HWND)
    widget.future=completed(stale)
    widget.tick()
    assert widget.frame is None
    assert not engine.graph_mag.isVisible()
