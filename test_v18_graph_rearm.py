"""V18: native MagEq visibility regression with cached valid fit."""
from types import SimpleNamespace
import native_eq_mag_v06 as native
from native_eq_mag_v06 import NativeAutoEQMag
class Geo:
    def __init__(self,rect):self.rect=rect
    def getRect(self):return self.rect
class Graph:
    def __init__(self,source,frame,rect):
        self.mageq_source=source
        self.mageq_frame=frame
        self.rect=rect
        self.visible=False
        self.updated=0
    def geometry(self):return Geo(self.rect)
    def isVisible(self):return self.visible
    def setGeometry(self,*rect):self.rect=rect
    def set_mageq(self,source=None,frame=None):
        self.mageq_source=source;self.mageq_frame=frame;self.updated+=1
class Engine:
    def __init__(self,graph):
        self.graph_mag=graph
        self.refreshed=0
    def refresh_visibility(self):
        self.refreshed+=1
        self.graph_mag.visible=bool(self.graph_mag.mageq_source)
def test_hidden_cached_mageq_rearms_native_graph(monkeypatch):
    monkeypatch.setattr(native,"frame_is_fresh_for_window",lambda *a:True)
    source=SimpleNamespace(source_identity="verified")
    frame=SimpleNamespace(plot=(252,553,1442,398),source_identity="verified",
                          identity_verified=True,hwnd=123)
    graph=Graph(source,frame,frame.plot)
    engine=Engine(graph)
    hub=SimpleNamespace(engine=engine,active="eq",workspace_visible=True,
                        isVisible=lambda:True,_eq_tick_safe=lambda:True)
    widget=SimpleNamespace(hub=hub,source=source,frame=frame,enabled=True,
                           _source_binding_ok=lambda **_:True)
    NativeAutoEQMag._sync_sum_renderer(widget)
    assert graph.isVisible() is True
    assert engine.refreshed>=1
    assert graph.updated==0 # no duplicate rendering, only re-show
def test_native_mageq_fail_closed_if_selected_tick_changed():
    source=object()
    frame=SimpleNamespace(plot=(252,553,1442,398))
    graph=Graph(source,frame,frame.plot)
    graph.visible=True
    engine=Engine(graph)
    hub=SimpleNamespace(engine=engine,active="eq",workspace_visible=True,
                        isVisible=lambda:True,_eq_tick_safe=lambda:False)
    widget=SimpleNamespace(hub=hub,source=source,frame=frame,enabled=True,
                           _source_binding_ok=lambda **_:True)
    NativeAutoEQMag._sync_sum_renderer(widget)
    assert graph.mageq_source is None and not graph.isVisible()
